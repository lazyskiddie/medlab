from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import LabReport
from .serializers import LabReportSerializer, LabReportUploadSerializer
from analysis.tasks import run_analysis_pipeline

ALLOWED_TYPES = {'image/jpeg', 'image/jpg', 'image/png', 'application/pdf'}
MAX_FILE_SIZE = 20 * 1024 * 1024


def _make_report(file, user):
    ft     = 'pdf' if file.content_type == 'application/pdf' else 'image'
    report = LabReport.objects.create(
        uploaded_by=user, file=file, file_type=ft,
        original_name=file.name, status=LabReport.Status.PENDING,
    )
    task = run_analysis_pipeline.delay(str(report.id))
    report.celery_task_id = task.id
    report.save(update_fields=['celery_task_id'])
    return report


class UploadReportView(APIView):
    parser_classes     = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LabReportUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        report = _make_report(serializer.validated_data['file'], request.user)
        return Response(LabReportSerializer(report).data, status=status.HTTP_201_CREATED)


class BulkUploadReportView(APIView):
    parser_classes     = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files received.'}, status=status.HTTP_400_BAD_REQUEST)
        created, rejected = [], []
        for file in files:
            if file.content_type not in ALLOWED_TYPES:
                rejected.append({'name': file.name, 'reason': 'Unsupported type'}); continue
            if file.size > MAX_FILE_SIZE:
                rejected.append({'name': file.name, 'reason': 'Exceeds 20MB'}); continue
            report = _make_report(file, request.user)
            created.append({'id': str(report.id), 'original_name': report.original_name})
        return Response(
            {'submitted': len(created), 'rejected': len(rejected),
             'reports': created, 'errors': rejected},
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
        )


class ReportListView(generics.ListAPIView):
    serializer_class   = LabReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = LabReport.objects.all() if self.request.user.is_staff \
             else LabReport.objects.filter(uploaded_by=self.request.user)
        qs = qs.select_related('result')
        s  = self.request.query_params.get('status')
        return qs.filter(status=s) if s else qs


class ReportDetailView(generics.RetrieveDestroyAPIView):
    serializer_class   = LabReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LabReport.objects.all().select_related('result') if self.request.user.is_staff \
               else LabReport.objects.filter(uploaded_by=self.request.user).select_related('result')

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    def perform_destroy(self, instance):
        if instance.file:
            try: instance.file.delete(save=False)
            except Exception: pass
        instance.delete()