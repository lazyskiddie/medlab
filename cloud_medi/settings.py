import os
from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY    = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG         = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_results',
    'django_celery_beat',
    'accounts',
    'reports',
    'analysis',
    'training.apps.TrainingConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cloud_medi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS':    [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cloud_medi.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'db.sqlite3',
        'OPTIONS': {'timeout': 20},
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

STATIC_URL       = '/static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {'anon': '20/hour', 'user': '200/hour'},
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': False,
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS   = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
).split(',')

CELERY_BROKER_URL         = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND     = 'django-db'
CELERY_CACHE_BACKEND      = 'django-cache'
CELERY_ACCEPT_CONTENT     = ['json']
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
CELERY_TIMEZONE           = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT    = 60 * 60 * 3
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 60 * 2

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'daily-auto-training-check': {
        'task':     'analysis.tasks.check_and_trigger_auto_training',
        'schedule': crontab(hour=2, minute=0),
    },
    'weekly-force-training': {
        'task':     'training.tasks.force_weekly_training',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    'cleanup-stale-processing': {
        'task':     'analysis.tasks.cleanup_stale_reports',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}

MODELS_DIR            = BASE_DIR / 'ml_models'
NER_MODEL_NAME        = config('NER_MODEL_NAME',        default='d4data/biomedical-ner-all')
SUMMARIZER_MODEL_NAME = config('SUMMARIZER_MODEL_NAME', default='google/flan-t5-base')
LOCAL_NER_PATH        = MODELS_DIR / 'ner'
LOCAL_SUMMARIZER_PATH = MODELS_DIR / 'summarizer'

TESSERACT_CMD      = config('TESSERACT_CMD', default='/usr/bin/tesseract')
REPORTS_OUTPUT_DIR = MEDIA_ROOT / 'output_reports'

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name} — {message}', 'style': '{'},
        'simple':  {'format': '[{asctime}] {levelname} {name} — {message}', 'style': '{'},
    },
    'handlers': {
        'console':       {'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'file':          {'class': 'logging.handlers.RotatingFileHandler',
                          'filename': LOGS_DIR / 'medlab.log',
                          'maxBytes': 10*1024*1024, 'backupCount': 5, 'formatter': 'verbose'},
        'analysis_file': {'class': 'logging.handlers.RotatingFileHandler',
                          'filename': LOGS_DIR / 'analysis.log',
                          'maxBytes': 20*1024*1024, 'backupCount': 10, 'formatter': 'verbose'},
        'training_file': {'class': 'logging.handlers.RotatingFileHandler',
                          'filename': LOGS_DIR / 'training.log',
                          'maxBytes': 50*1024*1024, 'backupCount': 5, 'formatter': 'verbose'},
        'error_file':    {'class': 'logging.handlers.RotatingFileHandler',
                          'filename': LOGS_DIR / 'errors.log',
                          'maxBytes': 5*1024*1024, 'backupCount': 5,
                          'formatter': 'verbose', 'level': 'ERROR'},
    },
    'loggers': {
        'django':    {'handlers': ['console', 'file'],          'level': 'INFO',  'propagate': False},
        'analysis':  {'handlers': ['console', 'analysis_file', 'error_file'], 'level': 'DEBUG' if DEBUG else 'INFO', 'propagate': False},
        'training':  {'handlers': ['console', 'training_file', 'error_file'], 'level': 'DEBUG' if DEBUG else 'INFO', 'propagate': False},
        'reports':   {'handlers': ['console', 'file', 'error_file'], 'level': 'INFO', 'propagate': False},
        'celery':    {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
    'root': {'handlers': ['console', 'file', 'error_file'], 'level': 'WARNING'},
}

ADMIN_SITE_HEADER = 'MedLab Administration'
ADMIN_SITE_TITLE  = 'MedLab Admin'
ADMIN_INDEX_TITLE = 'MedLab Control Panel'

DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER      = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    X_FRAME_OPTIONS                = 'DENY'
    SECURE_SSL_REDIRECT            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True