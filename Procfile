web:    python manage.py runserver 0.0.0.0:8000
worker: celery -A cloud_medi worker --loglevel=info
beat:   celery -A cloud_medi beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler