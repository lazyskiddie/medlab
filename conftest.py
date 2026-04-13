import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloud_medi.settings')

def pytest_configure(config):
    from django.conf import settings
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CACHES = {
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
    }
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    import tempfile
    settings.MEDIA_ROOT = tempfile.mkdtemp()
    settings.LOCAL_NER_PATH        = settings.MEDIA_ROOT + '/ner'
    settings.LOCAL_SUMMARIZER_PATH = settings.MEDIA_ROOT + '/summarizer'
    settings.MODELS_DIR            = settings.MEDIA_ROOT + '/ml_models'