import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_analysis_pipeline(self, report_id: str):
    from reports.models import LabReport, AnalysisResult
    from analysis.ocr import extract_text
    from analysis.rules import run_rule_engine
    from analysis.nlp import generate_summary, detect_conditions
    from analysis.pdf_report import generate_pdf_report

    try:
        report = LabReport.objects.get(id=report_id)
    except LabReport.DoesNotExist:
        logger.error(f'Report {report_id} not found.')
        return

    report.status = LabReport.Status.PROCESSING
    report.save(update_fields=['status'])

    try:
        # Step 1: OCR
        raw_text = extract_text(report.file.path, report.file_type)
        logger.info(f'[{report_id}] OCR done — {len(raw_text)} chars.')

        # Step 2: Rule engine
        gender      = getattr(report.uploaded_by, 'gender', 'all') or 'all'
        rule_output = run_rule_engine(raw_text, gender=gender)
        flagged     = rule_output['flagged_items']
        extracted   = rule_output['extracted_values']
        severity    = rule_output['severity']

        # Step 3: NLP summary
        summary    = generate_summary(flagged, extracted)
        conditions = detect_conditions(flagged)

        # Step 4: Save to DB
        result, _ = AnalysisResult.objects.get_or_create(report=report)
        result.raw_text             = raw_text
        result.extracted_values     = extracted
        result.flagged_items        = flagged
        result.summary              = summary
        result.conditions_detected  = conditions
        result.severity             = severity
        result.save()

        # Step 5: PDF
        pdf_path = generate_pdf_report(result)
        if pdf_path:
            result.pdf_report = pdf_path
            result.save(update_fields=['pdf_report'])

        # Step 6: Seed training data
        _seed_training_from_result(report, result, raw_text)

        # Step 7: Mark complete
        report.status = LabReport.Status.COMPLETED
        report.save(update_fields=['status'])
        logger.info(f'[{report_id}] Pipeline complete.')

        # Step 8: Check auto-training threshold
        check_and_trigger_auto_training.delay()

    except Exception as exc:
        logger.error(f'[{report_id}] Pipeline failed: {exc}', exc_info=True)
        report.status = LabReport.Status.FAILED
        report.save(update_fields=['status'])
        raise self.retry(exc=exc)


def _seed_training_from_result(report, result, raw_text: str):
    from training.models import TrainingReport
    import shutil
    from pathlib import Path
    from django.conf import settings
    import uuid as _uuid

    try:
        src     = Path(report.file.path)
        dst_dir = Path(settings.MEDIA_ROOT) / 'training_data' / 'user_uploads'
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst      = dst_dir / f'{_uuid.uuid4()}_{src.name}'
        shutil.copy2(src, dst)
        rel_path = dst.relative_to(Path(settings.MEDIA_ROOT))

        tr, created = TrainingReport.objects.get_or_create(
            lab_report=report,
            defaults={
                'uploaded_by':        report.uploaded_by,
                'source':             TrainingReport.Source.USER_UPLOAD,
                'file':               str(rel_path),
                'file_type':          report.file_type,
                'raw_ocr_text':       raw_text,
                'correct_summary':    result.summary,
                'correct_conditions': result.conditions_detected,
                'correct_severity':   result.severity,
                'is_processed':       True,
                'is_doctor_reviewed': False,
            },
        )
        if not created and not tr.is_doctor_reviewed:
            tr.raw_ocr_text       = raw_text
            tr.correct_summary    = result.summary
            tr.correct_conditions = result.conditions_detected
            tr.correct_severity   = result.severity
            tr.is_processed       = True
            tr.save(update_fields=['raw_ocr_text', 'correct_summary',
                                   'correct_conditions', 'correct_severity', 'is_processed'])
        logger.info(f'Training seeded from {report.id} ({"created" if created else "updated"}).')
    except Exception as e:
        logger.error(f'Failed to seed training from {report.id}: {e}')


@shared_task
def check_and_trigger_auto_training():
    from training.models import TrainingReport, FineTuningJob, AutoTrainingConfig
    from training.tasks import trigger_finetuning
    from django.utils import timezone

    config = AutoTrainingConfig.get()
    if not config.auto_training_enabled:
        return

    base_qs = TrainingReport.objects.filter(is_processed=True)
    if not config.include_unreviewed:
        base_qs = base_qs.filter(is_doctor_reviewed=True)

    total          = base_qs.count()
    new_since_last = total - config.samples_at_last_trigger

    if new_since_last < config.new_samples_threshold:
        return

    if FineTuningJob.objects.filter(status=FineTuningJob.JobStatus.RUNNING).exists():
        return

    job = FineTuningJob.objects.create(triggered_by=None, base_model='google/flan-t5-base')
    trigger_finetuning.delay(str(job.id))

    config.last_auto_trigger_at    = timezone.now()
    config.samples_at_last_trigger = total
    config.save(update_fields=['last_auto_trigger_at', 'samples_at_last_trigger'])
    logger.info(f'Auto fine-tuning triggered. Job={job.id}, samples={total}.')


@shared_task
def cleanup_stale_reports():
    from reports.models import LabReport
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=2)
    stale  = LabReport.objects.filter(
        status=LabReport.Status.PROCESSING,
        updated_at__lt=cutoff,
    )
    count = stale.count()
    if count:
        stale.update(status=LabReport.Status.FAILED)
        logger.warning(f'Cleaned up {count} stale reports.')
    return count