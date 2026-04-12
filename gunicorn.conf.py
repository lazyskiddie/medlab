# gunicorn.conf.py
# Production WSGI server config for MedLab
# Usage: gunicorn -c gunicorn.conf.py cloud_medi.wsgi:application

import multiprocessing
from pathlib import Path

# ── Binding ───────────────────────────────────────────────────────────────────
bind    = '0.0.0.0:8000'
backlog = 2048

# ── Workers ───────────────────────────────────────────────────────────────────
# Formula: 2 * CPU cores + 1
# Sync workers are fine — analysis is offloaded to Celery
workers     = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
threads      = 2
timeout      = 120          # 2 min — long for analysis status checks
keepalive    = 5
max_requests = 1000         # recycle workers to prevent memory leaks
max_requests_jitter = 50

# ── Logging ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
LOGS_DIR   = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

accesslog  = str(LOGS_DIR / 'gunicorn_access.log')
errorlog   = str(LOGS_DIR / 'gunicorn_error.log')
loglevel   = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sms'

# ── Process ───────────────────────────────────────────────────────────────────
proc_name  = 'medlab'
pidfile    = str(BASE_DIR / 'gunicorn.pid')
daemon     = False          # keep False — let systemd/supervisor manage it

# ── Security ──────────────────────────────────────────────────────────────────
limit_request_line   = 8190
limit_request_fields = 100
forwarded_allow_ips  = '*'  # trust X-Forwarded-For from nginx