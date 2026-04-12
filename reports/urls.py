from django.urls import path
from .views import UploadReportView, BulkUploadReportView, ReportListView, ReportDetailView

urlpatterns = [
    path('upload/',      UploadReportView.as_view(),     name='report-upload'),
    path('bulk-upload/', BulkUploadReportView.as_view(), name='report-bulk-upload'),
    path('',             ReportListView.as_view(),        name='report-list'),
    path('<uuid:pk>/',   ReportDetailView.as_view(),      name='report-detail'),
]