from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

admin.site.site_header = 'MedLab Administration'
admin.site.site_title  = 'MedLab Admin'
admin.site.index_title = 'MedLab Control Panel'


def health_check(request):
    from django.db import connection
    try:
        connection.ensure_connection()
        db_status = 'ok'
    except Exception:
        db_status = 'error'
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'database': db_status,
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/accounts/', include('accounts.urls')),
    path('api/reports/',  include('reports.urls')),
    path('api/analysis/', include('analysis.urls')),
    path('api/training/', include('training.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)