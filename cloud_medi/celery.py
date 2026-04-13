import os
from celery import Celery
from celery.signals import worker_ready, task_failure

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloud_medi.settings')

app = Celery('cloud_medi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    import logging
    from django.conf import settings
    from pathlib import Path
    logger = logging.getLogger('celery')
    ner_ready  = Path(settings.LOCAL_NER_PATH).exists()
    summ_ready = Path(settings.LOCAL_SUMMARIZER_PATH).exists()
    ft_ready   = (Path(settings.MODELS_DIR) / 'summarizer_finetuned').exists()
    logger.info(
        f'Celery worker ready. '
        f'NER: {"OK" if ner_ready else "MISSING"}. '
        f'Summarizer: {"OK" if summ_ready else "MISSING"}. '
        f'Fine-tuned: {"OK" if ft_ready else "not yet trained"}.'
    )

@task_failure.connect
def on_task_failure(sender, task_id, exception, traceback, einfo, **kwargs):
    import logging
    logging.getLogger('celery').error(f'Task {sender.name} [{task_id}] failed: {exception}')

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')