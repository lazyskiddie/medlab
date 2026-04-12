from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from reports.models import LabReport
from analysis.tasks import run_analysis_pipeline


class AnalysisStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_id):
        qs     = LabReport.objects.all() if request.user.is_staff \
                 else LabReport.objects.filter(uploaded_by=request.user)
        report = get_object_or_404(qs, id=report_id)
        return Response({'status': report.status, 'report_id': str(report.id)})


class RetriggerAnalysisView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, report_id):
        report        = get_object_or_404(LabReport, id=report_id)
        report.status = LabReport.Status.PENDING
        report.save(update_fields=['status'])
        task = run_analysis_pipeline.delay(str(report.id))
        report.celery_task_id = task.id
        report.save(update_fields=['celery_task_id'])
        return Response({'message': 'Analysis re-triggered.', 'task_id': task.id})