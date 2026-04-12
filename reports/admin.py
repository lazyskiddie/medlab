from django.contrib import admin
from .models import LabReport, AnalysisResult


class AnalysisResultInline(admin.StackedInline):
    model       = AnalysisResult
    extra       = 0
    can_delete  = False
    readonly_fields = ('raw_text', 'extracted_values', 'flagged_items',
                       'summary', 'conditions_detected', 'severity', 'pdf_report', 'created_at')


@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    list_display  = ('id', 'uploaded_by', 'file_type', 'status', 'uploaded_at')
    list_filter   = ('status', 'file_type')
    search_fields = ('uploaded_by__username',)
    readonly_fields = ('id', 'celery_task_id', 'uploaded_at', 'updated_at')
    inlines       = [AnalysisResultInline]


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display  = ('id', 'report', 'severity', 'created_at')
    list_filter   = ('severity',)
    readonly_fields = ('id', 'created_at', 'raw_text', 'extracted_values',
                       'flagged_items', 'conditions_detected')