from rest_framework import serializers
from .models import TrainingReport, FineTuningJob, AutoTrainingConfig


class TrainingReportSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)
    reviewed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = TrainingReport
        fields = ('id', 'source', 'uploaded_by', 'lab_report', 'file', 'file_type',
                  'correct_summary', 'correct_conditions', 'correct_severity',
                  'is_processed', 'is_doctor_reviewed', 'reviewed_by', 'reviewed_at', 'uploaded_at')
        read_only_fields = ('id', 'source', 'uploaded_by', 'lab_report', 'is_processed',
                            'is_doctor_reviewed', 'reviewed_by', 'reviewed_at', 'uploaded_at')


class FineTuningJobSerializer(serializers.ModelSerializer):
    triggered_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = FineTuningJob
        fields = ('id', 'status', 'base_model', 'triggered_by', 'samples_used',
                  'output_path', 'logs', 'started_at', 'completed_at', 'created_at')
        read_only_fields = ('id', 'status', 'triggered_by', 'samples_used',
                            'output_path', 'logs', 'started_at', 'completed_at', 'created_at')