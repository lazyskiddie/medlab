import logging
from datetime import datetime
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def build_weighted_dataset(config):
    from training.models import TrainingReport
    from datasets import Dataset
    import math

    records = []

    for tr in TrainingReport.objects.filter(
        is_processed=True, is_doctor_reviewed=True,
        correct_summary__gt='', raw_ocr_text__gt='',
    ):
        prompt = f"Analyze this medical lab report and write a patient-friendly summary:\n\n{tr.raw_ocr_text[:1500]}"
        records.append({'input': prompt, 'output': tr.correct_summary, 'weight': 1.0})

    if config.include_unreviewed:
        weight = float(config.unreviewed_weight)
        for tr in TrainingReport.objects.filter(
            is_processed=True, is_doctor_reviewed=False,
            correct_summary__gt='', raw_ocr_text__gt='',
        ):
            prompt = f"Analyze this medical lab report and write a patient-friendly summary:\n\n{tr.raw_ocr_text[:1500]}"
            records.append({'input': prompt, 'output': tr.correct_summary, 'weight': weight})

    if not records:
        raise ValueError('No usable training records found.')

    oversampled = []
    for r in records:
        repeat = max(1, math.ceil(r['weight'] * 2))
        oversampled.extend([{'input': r['input'], 'output': r['output']}] * repeat)

    return Dataset.from_list(oversampled), len(records)


def run_finetuning(job_id: str):
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
        finetuned = Path(settings.MODELS_DIR) / 'summarizer_finetuned'
        local     = Path(settings.LOCAL_SUMMARIZER_PATH)
        if finetuned.exists() and any(finetuned.iterdir()):
            model_name = str(finetuned)
        elif local.exists():
            model_name = str(local)
        else:
            model_name = job.base_model

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model     = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        raw_dataset, total_records = build_weighted_dataset(config)
        if total_records < 3:
            raise ValueError(f'Need at least 3 training records, found {total_records}.')

        split = raw_dataset.train_test_split(
            test_size=min(0.15, 10 / len(raw_dataset)), seed=42)

        def tokenize(batch):
            model_inputs = tokenizer(batch['input'], max_length=512,
                                     padding='max_length', truncation=True)
            with tokenizer.as_target_tokenizer():
                labels = tokenizer(batch['output'], max_length=256,
                                   padding='max_length', truncation=True)
            model_inputs['labels'] = labels['input_ids']
            return model_inputs

        tokenised     = split.map(tokenize, batched=True, remove_columns=['input', 'output'])
        data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)
        epochs        = 3 if total_records >= 20 else 5

        training_args = Seq2SeqTrainingArguments(
            output_dir=str(output_path),
            num_train_epochs=epochs,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            warmup_steps=max(10, total_records // 5),
            weight_decay=0.01,
            logging_steps=5,
            evaluation_strategy='epoch',
            save_strategy='epoch',
            load_best_model_at_end=True,
            predict_with_generate=True,
            fp16=False,
            report_to='none',
        )

        trainer = Seq2SeqTrainer(
            model=model, args=training_args,
            train_dataset=tokenised['train'],
            eval_dataset=tokenised['test'],
            tokenizer=tokenizer,
            data_collator=data_collator,
        )

        trainer.train()
        trainer.save_model(str(output_path))
        tokenizer.save_pretrained(str(output_path))

        job.status       = FineTuningJob.JobStatus.COMPLETED
        job.output_path  = str(output_path)
        job.samples_used = total_records
        job.completed_at = datetime.now()
        job.logs         = f'Training complete. {total_records} records, {epochs} epochs.'
        job.save()

    except Exception as e:
        logger.error(f'Fine-tuning {job_id} failed: {e}', exc_info=True)
        job.status = FineTuningJob.JobStatus.FAILED
        job.logs   = str(e)
        job.save(update_fields=['status', 'logs'])
        raise