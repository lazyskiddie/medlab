import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloud_medi.settings')

app = Celery('cloud_medi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()