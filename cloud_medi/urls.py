from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

admin.site.site_header  = 'MedLab Administration'
admin.site.site_title   = 'MedLab Admin'
admin.site.index_title  = 'MedLab Control Panel'


def health_check(request):
    from django.db import connection
    from pathlib import Path
    try:
        connection.ensure_connection()
        from reports.models import LabReport
        db_ok = True
        report_count = LabReport.objects.count()
    except Exception:
        db_ok = False
        report_count = 0

    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    ner_ok  = Path(settings.LOCAL_NER_PATH).exists()
    summ_ok = Path(settings.LOCAL_SUMMARIZER_PATH).exists()

    return JsonResponse({
        'status':    'ok' if db_ok else 'degraded',
        'timestamp': timezone.now().isoformat(),
        'version':   '1.0.0',
        'details': {
            'database': {'status': 'ok' if db_ok else 'error', 'reports_count': report_count},
            'redis':    {'status': 'ok' if redis_ok else 'error'},
            'models':   {
                'ner':            'ok' if ner_ok  else 'missing',
                'summarizer':     'ok' if summ_ok else 'missing',
                'analysis_ready': ner_ok and summ_ok,
            },
        },
    }, status=200 if db_ok else 503)


urlpatterns = [
    path('admin/',                   admin.site.urls),
    path('api/health/',              health_check,                   name='health-check'),
    path('api/auth/token/',          TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('api/auth/token/refresh/',  TokenRefreshView.as_view(),     name='token_refresh'),
    path('api/accounts/',            include('accounts.urls')),
    path('api/reports/',             include('reports.urls')),
    path('api/analysis/',            include('analysis.urls')),
    path('api/training/',            include('training.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)