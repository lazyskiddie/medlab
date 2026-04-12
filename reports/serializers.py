from rest_framework import serializers
from .models import LabReport, AnalysisResult


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AnalysisResult
        fields = ('id', 'raw_text', 'extracted_values', 'flagged_items',
                  'summary', 'conditions_detected', 'severity', 'pdf_report', 'created_at')


class LabReportSerializer(serializers.ModelSerializer):
    result      = AnalysisResultSerializer(read_only=True)
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = LabReport
        fields = ('id', 'uploaded_by', 'file', 'file_type', 'original_name',
                  'status', 'celery_task_id', 'uploaded_at', 'updated_at', 'result')
        read_only_fields = ('id', 'uploaded_by', 'file_type', 'original_name',
                            'status', 'celery_task_id', 'uploaded_at', 'updated_at')


class LabReportUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LabReport
        fields = ('file',)

    def validate_file(self, value):
        allowed = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
        if value.content_type not in allowed:
            raise serializers.ValidationError('Only JPG, PNG, and PDF files are allowed.')
        if value.size > 20 * 1024 * 1024:
            raise serializers.ValidationError('File size must be under 20MB.')
        return value