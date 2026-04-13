import multiprocessing
from pathlib import Path

bind        = '0.0.0.0:8000'
workers     = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
threads     = 2
timeout     = 120
keepalive   = 5
max_requests = 1000
max_requests_jitter = 50

BASE_DIR  = Path(__file__).resolve().parent
LOGS_DIR  = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

accesslog = str(LOGS_DIR / 'gunicorn_access.log')
errorlog  = str(LOGS_DIR / 'gunicorn_error.log')
loglevel  = 'info'
proc_name = 'medlab'
daemon    = False
forwarded_allow_ips = '*'