from django.urls import path
from .views import (
    TrainingReportListCreateView, MarkReviewedView,
    FineTuningJobListCreateView, StartFineTuningView, TrainingStatsView,
)

urlpatterns = [
    path('data/',                     TrainingReportListCreateView.as_view(), name='training-data'),
    path('data/<uuid:pk>/review/',    MarkReviewedView.as_view(),             name='training-review'),
    path('jobs/',                     FineTuningJobListCreateView.as_view(),  name='training-jobs'),
    path('jobs/<uuid:job_id>/start/', StartFineTuningView.as_view(),          name='training-start'),
    path('stats/',                    TrainingStatsView.as_view(),            name='training-stats'),
]