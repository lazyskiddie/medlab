from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import TrainingReport, FineTuningJob, AutoTrainingConfig
from .serializers import TrainingReportSerializer, FineTuningJobSerializer
from .tasks import ocr_training_report, trigger_finetuning


class TrainingReportListCreateView(generics.ListCreateAPIView):
    queryset           = TrainingReport.objects.all()
    serializer_class   = TrainingReportSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs       = super().get_queryset()
        source   = self.request.query_params.get('source')
        reviewed = self.request.query_params.get('reviewed')
        if source:
            qs = qs.filter(source=source)
        if reviewed is not None:
            qs = qs.filter(is_doctor_reviewed=reviewed.lower() == 'true')
        return qs

    def perform_create(self, serializer):
        file = self.request.data.get('file')
        ct   = getattr(file, 'content_type', '')
        ft   = 'pdf' if 'pdf' in ct else 'image'
        instance = serializer.save(uploaded_by=self.request.user,
                                   file_type=ft, source=TrainingReport.Source.ADMIN)
        ocr_training_report.delay(str(instance.id))


class MarkReviewedView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        tr = get_object_or_404(TrainingReport, pk=pk)
        if 'correct_summary' in request.data:
            tr.correct_summary = request.data['correct_summary']
        if 'correct_conditions' in request.data:
            tr.correct_conditions = request.data['correct_conditions']
        if 'correct_severity' in request.data:
            tr.correct_severity = request.data['correct_severity']
        tr.is_doctor_reviewed = True
        tr.reviewed_by        = request.user
        tr.reviewed_at        = timezone.now()
        tr.save()
        return Response({'message': 'Marked as doctor-reviewed.', 'id': str(tr.id)})


class FineTuningJobListCreateView(generics.ListCreateAPIView):
    queryset           = FineTuningJob.objects.all()
    serializer_class   = FineTuningJobSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(triggered_by=self.request.user)


class StartFineTuningView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, job_id):
        job = get_object_or_404(FineTuningJob, id=job_id)
        if job.status == FineTuningJob.JobStatus.RUNNING:
            return Response({'error': 'Job is already running.'}, status=status.HTTP_400_BAD_REQUEST)
        trigger_finetuning.delay(str(job.id))
        return Response({'message': 'Fine-tuning job queued.', 'job_id': str(job.id)})


class TrainingStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from reports.models import LabReport
        config = AutoTrainingConfig.get()
        total  = TrainingReport.objects.filter(is_processed=True)
        return Response({
            'training_data': {
                'total_processed':   total.count(),
                'from_user_uploads': total.filter(source=TrainingReport.Source.USER_UPLOAD).count(),
                'from_admin':        total.filter(source=TrainingReport.Source.ADMIN).count(),
                'doctor_reviewed':   total.filter(is_doctor_reviewed=True).count(),
                'pending_review':    total.filter(is_doctor_reviewed=False).count(),
            },
            'lab_reports': {
                'total':      LabReport.objects.count(),
                'completed':  LabReport.objects.filter(status='completed').count(),
                'processing': LabReport.objects.filter(status='processing').count(),
                'failed':     LabReport.objects.filter(status='failed').count(),
            },
            'finetuning': {
                'total_jobs':     FineTuningJob.objects.count(),
                'completed_jobs': FineTuningJob.objects.filter(status='completed').count(),
                'running_jobs':   FineTuningJob.objects.filter(status='running').count(),
            },
            'auto_training': {
                'enabled':               config.auto_training_enabled,
                'threshold':             config.new_samples_threshold,
                'samples_since_last':    total.count() - config.samples_at_last_trigger,
                'last_trigger':          config.last_auto_trigger_at,
            },
        })