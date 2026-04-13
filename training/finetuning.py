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
            correct_summary__gt='', raw_ocr_text__gt=''):
        records.append({'input': f'Analyze this lab report:\n\n{tr.raw_ocr_text[:1500]}',
                        'output': tr.correct_summary, 'weight': 1.0})

    if config.include_unreviewed:
        for tr in TrainingReport.objects.filter(
                is_processed=True, is_doctor_reviewed=False,
                correct_summary__gt='', raw_ocr_text__gt=''):
            records.append({'input': f'Analyze this lab report:\n\n{tr.raw_ocr_text[:1500]}',
                            'output': tr.correct_summary, 'weight': float(config.unreviewed_weight)})

    if not records:
        raise ValueError('No usable training records found.')

    oversampled = []
    for r in records:
        repeat = max(1, math.ceil(r['weight'] * 2))
        oversampled.extend([{'input': r['input'], 'output': r['output']}] * repeat)

    return Dataset.from_list(oversampled), len(records)


def run_finetuning(job_id: str):
    from training.models import FineTuningJob, AutoTrainingConfig
    from transformers import (AutoTokenizer, AutoModelForSeq2SeqLM,
                              Seq2SeqTrainer, Seq2SeqTrainingArguments,
                              DataCollatorForSeq2Seq)

    job = FineTuningJob.objects.get(id=job_id)
    job.status     = FineTuningJob.JobStatus.RUNNING
    job.started_at = datetime.now()
    job.save(update_fields=['status', 'started_at'])

    output_path = Path(settings.MODELS_DIR) / 'summarizer_finetuned'
    output_path.mkdir(parents=True, exist_ok=True)
    config = AutoTrainingConfig.get()

    try:
        ft    = Path(settings.MODELS_DIR) / 'summarizer_finetuned'
        local = Path(settings.LOCAL_SUMMARIZER_PATH)
        if ft.exists() and any(ft.iterdir()):   name = str(ft)
        elif local.exists():                     name = str(local)
        else:                                    name = job.base_model

        tokenizer = AutoTokenizer.from_pretrained(name)
        model     = AutoModelForSeq2SeqLM.from_pretrained(name)

        raw_dataset, total = build_weighted_dataset(config)
        if total < 3:
            raise ValueError(f'Need at least 3 training records, found {total}.')

        split = raw_dataset.train_test_split(test_size=min(0.15, 10/len(raw_dataset)), seed=42)

        def tokenize(batch):
            inputs = tokenizer(batch['input'],  max_length=512, padding='max_length', truncation=True)
            with tokenizer.as_target_tokenizer():
                labels = tokenizer(batch['output'], max_length=256, padding='max_length', truncation=True)
            inputs['labels'] = labels['input_ids']
            return inputs

        tokenised = split.map(tokenize, batched=True, remove_columns=['input','output'])
        collator  = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)
        epochs    = 3 if total >= 20 else 5

        args = Seq2SeqTrainingArguments(
            output_dir=str(output_path), num_train_epochs=epochs,
            per_device_train_batch_size=4, per_device_eval_batch_size=4,
            warmup_steps=max(10, total//5), weight_decay=0.01,
            evaluation_strategy='epoch', save_strategy='epoch',
            load_best_model_at_end=True, predict_with_generate=True,
            fp16=False, report_to='none',
        )
        trainer = Seq2SeqTrainer(
            model=model, args=args,
            train_dataset=tokenised['train'], eval_dataset=tokenised['test'],
            tokenizer=tokenizer, data_collator=collator,
        )
        trainer.train()
        trainer.save_model(str(output_path))
        tokenizer.save_pretrained(str(output_path))

        job.status       = FineTuningJob.JobStatus.COMPLETED
        job.output_path  = str(output_path)
        job.samples_used = total
        job.completed_at = datetime.now()
        job.logs         = f'Done. {total} records, {epochs} epochs.'
        job.save()

    except Exception as e:
        logger.error(f'Fine-tuning {job_id} failed: {e}', exc_info=True)
        job.status = FineTuningJob.JobStatus.FAILED
        job.logs   = str(e)
        job.save(update_fields=['status', 'logs'])
        raise