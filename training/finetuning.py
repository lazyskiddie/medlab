"""
Local fine-tuning pipeline.
Trains FLAN-T5 on ALL training data — both user uploads (auto-seeded)
and admin-annotated records. Reviewed records get higher sample weight.
Zero external API calls. Everything stays on the local server.
"""
import logging
from datetime import datetime
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def build_weighted_dataset(config):
    """
    Pull all usable TrainingReport records from SQLite and build a
    Hugging Face Dataset with weighted oversampling so that
    doctor-reviewed records (weight=1.0) appear more often than
    unreviewed user-upload records (weight=config.unreviewed_weight).

    Returns: (Dataset, int total_records)
    """
    from training.models import TrainingReport
    from datasets import Dataset

    records = []

    # ── Admin / doctor-reviewed records (weight = 1.0, full repetition) ──
    reviewed_qs = TrainingReport.objects.filter(
        is_processed=True,
        is_doctor_reviewed=True,
        correct_summary__gt='',
        raw_ocr_text__gt='',
    )
    for tr in reviewed_qs:
        prompt = _build_prompt(tr.raw_ocr_text)
        records.append({'input': prompt, 'output': tr.correct_summary, 'weight': 1.0})

    # ── User-upload records (weight = config.unreviewed_weight) ──────────
    if config.include_unreviewed:
        unreviewed_qs = TrainingReport.objects.filter(
            is_processed=True,
            is_doctor_reviewed=False,
            correct_summary__gt='',
            raw_ocr_text__gt='',
        )
        weight = float(config.unreviewed_weight)
        for tr in unreviewed_qs:
            prompt = _build_prompt(tr.raw_ocr_text)
            records.append({'input': prompt, 'output': tr.correct_summary, 'weight': weight})

    if not records:
        raise ValueError(
            'No usable training records found. '
            'At least one processed TrainingReport with OCR text and a summary is required.'
        )

    # Oversample reviewed records to give them higher effective weight.
    # Simple strategy: duplicate reviewed records proportionally.
    import math
    oversampled = []
    for r in records:
        repeat = max(1, math.ceil(r['weight'] * 2))
        oversampled.extend([{'input': r['input'], 'output': r['output']}] * repeat)

    logger.info(
        f'Dataset: {len(records)} raw records → {len(oversampled)} after oversampling '
        f'(reviewed={reviewed_qs.count()}, unreviewed={len(records) - reviewed_qs.count()}).'
    )

    return Dataset.from_list(oversampled), len(records)


def _build_prompt(ocr_text: str) -> str:
    return (
        "Analyze the following medical lab report text and write a "
        "clear, patient-friendly summary of the findings:\n\n"
        f"{ocr_text[:1500]}"
    )


def run_finetuning(job_id: str):
    """
    Main fine-tuning entry point. Called from a Celery task.
    Saves fine-tuned weights to ml_models/summarizer_finetuned/
    and updates the FineTuningJob row in SQLite.
    """
    from training.models import FineTuningJob, AutoTrainingConfig
    from transformers import (
        AutoTokenizer, AutoModelForSeq2SeqLM,
        Seq2SeqTrainer, Seq2SeqTrainingArguments,
        DataCollatorForSeq2Seq,
    )

    job = FineTuningJob.objects.get(id=job_id)
    job.status     = FineTuningJob.JobStatus.RUNNING
    job.started_at = datetime.now()
    job.save(update_fields=['status', 'started_at'])

    output_path = Path(settings.MODELS_DIR) / 'summarizer_finetuned'
    output_path.mkdir(parents=True, exist_ok=True)

    config = AutoTrainingConfig.get()

    try:
        # ── Load base model ───────────────────────────────────────────────────
        local_path = Path(settings.LOCAL_SUMMARIZER_PATH)
        # If a previously fine-tuned model exists, continue from it
        finetuned_path = Path(settings.MODELS_DIR) / 'summarizer_finetuned'
        if finetuned_path.exists() and any(finetuned_path.iterdir()):
            model_name = str(finetuned_path)
            logger.info(f'[Job {job_id}] Continuing from fine-tuned model: {model_name}')
        elif local_path.exists():
            model_name = str(local_path)
            logger.info(f'[Job {job_id}] Starting from downloaded base model: {model_name}')
        else:
            model_name = job.base_model
            logger.info(f'[Job {job_id}] Starting from HuggingFace: {model_name}')

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model     = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        # ── Build dataset from SQLite ─────────────────────────────────────────
        raw_dataset, total_records = build_weighted_dataset(config)

        if total_records < 3:
            raise ValueError(
                f'Need at least 3 training records, found {total_records}. '
                'Wait for more user uploads or add admin-annotated records.'
            )

        # Train / validation split
        split = raw_dataset.train_test_split(test_size=min(0.15, 10 / len(raw_dataset)), seed=42)

        # ── Tokenise ──────────────────────────────────────────────────────────
        MAX_INPUT  = 512
        MAX_TARGET = 256

        def tokenize(batch):
            model_inputs = tokenizer(
                batch['input'],
                max_length=MAX_INPUT,
                padding='max_length',
                truncation=True,
            )
            with tokenizer.as_target_tokenizer():
                labels = tokenizer(
                    batch['output'],
                    max_length=MAX_TARGET,
                    padding='max_length',
                    truncation=True,
                )
            model_inputs['labels'] = labels['input_ids']
            return model_inputs

        tokenised = split.map(
            tokenize, batched=True,
            remove_columns=['input', 'output'],
        )

        data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)

        # ── Training arguments ────────────────────────────────────────────────
        # Fewer epochs for small datasets to avoid overfitting
        epochs = 3 if total_records >= 20 else 5

        training_args = Seq2SeqTrainingArguments(
            output_dir=str(output_path),
            num_train_epochs=epochs,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            warmup_steps=max(10, total_records // 5),
            weight_decay=0.01,
            logging_dir=str(output_path / 'logs'),
            logging_steps=5,
            evaluation_strategy='epoch',
            save_strategy='epoch',
            load_best_model_at_end=True,
            predict_with_generate=True,
            fp16=False,        # set True if CUDA GPU with float16 support
            report_to='none',  # no external tracking services
        )

        # ── Train ─────────────────────────────────────────────────────────────
        trainer = Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=tokenised['train'],
            eval_dataset=tokenised['test'],
            tokenizer=tokenizer,
            data_collator=data_collator,
        )

        logger.info(
            f'[Job {job_id}] Training started. '
            f'train={len(tokenised["train"])} eval={len(tokenised["test"])} '
            f'epochs={epochs}.'
        )
        trainer.train()

        # ── Save new weights ───────────────────────────────────────────────────
        trainer.save_model(str(output_path))
        tokenizer.save_pretrained(str(output_path))
        logger.info(f'[Job {job_id}] Model saved to {output_path}.')

        # Update LOCAL_SUMMARIZER_PATH to point at the fine-tuned model so
        # the next Celery worker restart picks it up automatically
        settings.LOCAL_SUMMARIZER_PATH = output_path

        log_msg = (
            f'Training complete. '
            f'{total_records} source records, {len(raw_dataset)} oversampled, '
            f'{epochs} epochs.'
        )

        job.status       = FineTuningJob.JobStatus.COMPLETED
        job.output_path  = str(output_path)
        job.samples_used = total_records
        job.completed_at = datetime.now()
        job.logs         = log_msg
        job.save()

        logger.info(f'[Job {job_id}] Fine-tuning complete. {log_msg}')

    except Exception as e:
        logger.error(f'[Job {job_id}] Fine-tuning failed: {e}', exc_info=True)
        job.status = FineTuningJob.JobStatus.FAILED
        job.logs   = str(e)
        job.save(update_fields=['status', 'logs'])
        raise