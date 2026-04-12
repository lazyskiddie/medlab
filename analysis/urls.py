from django.urls import path
from .views import AnalysisStatusView, RetriggerAnalysisView

urlpatterns = [
    path('status/<uuid:report_id>/',    AnalysisStatusView.as_view(),    name='analysis-status'),
    path('retrigger/<uuid:report_id>/', RetriggerAnalysisView.as_view(), name='analysis-retrigger'),
]