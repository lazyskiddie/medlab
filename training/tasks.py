import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1)
def ocr_training_report(self, training_report_id: str):
    from training.models import TrainingReport
    from analysis.ocr import extract_text
    try:
        tr   = TrainingReport.objects.get(id=training_report_id)
        text = extract_text(tr.file.path, tr.file_type)
        tr.raw_ocr_text = text
        tr.is_processed = True
        tr.save(update_fields=['raw_ocr_text', 'is_processed'])
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=1)
def trigger_finetuning(self, job_id: str):
    from training.finetuning import run_finetuning
    try:
        run_finetuning(job_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def force_weekly_training():
    from training.models import TrainingReport, FineTuningJob, AutoTrainingConfig
    from django.utils import timezone

    if FineTuningJob.objects.filter(status=FineTuningJob.JobStatus.RUNNING).exists():
        return
    sample_count = TrainingReport.objects.filter(is_processed=True).count()
    if sample_count < 3:
        return

    job = FineTuningJob.objects.create(triggered_by=None, base_model='google/flan-t5-base')
    trigger_finetuning.delay(str(job.id))

    config = AutoTrainingConfig.get()
    config.last_auto_trigger_at    = timezone.now()
    config.samples_at_last_trigger = sample_count
    config.save(update_fields=['last_auto_trigger_at', 'samples_at_last_trigger'])
    logger.info(f'Weekly training triggered. Job={job.id}')