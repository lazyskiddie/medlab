from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.utils import timezone
from .models import TrainingReport, FineTuningJob, AutoTrainingConfig
from .tasks import ocr_training_report, trigger_finetuning


@admin.register(TrainingReport)
class TrainingReportAdmin(admin.ModelAdmin):
    list_display  = ('id', 'source_badge', 'correct_severity',
                     'is_doctor_reviewed', 'is_processed', 'uploaded_at')
    list_filter   = ('source', 'is_doctor_reviewed', 'is_processed', 'correct_severity')
    search_fields = ('uploaded_by__username',)
    readonly_fields = ('id', 'source', 'uploaded_by', 'lab_report',
                       'raw_ocr_text', 'is_processed', 'uploaded_at', 'reviewed_at', 'reviewed_by')
    actions = ['mark_doctor_reviewed', 'run_ocr_on_selected']

    fieldsets = (
        ('Source', {'fields': ('id', 'source', 'uploaded_by', 'lab_report', 'file', 'file_type')}),
        ('Labels — edit to correct AI output', {
            'fields': ('correct_summary', 'correct_conditions', 'correct_severity'),
            'description': 'For user-upload records these are pre-filled by the AI. Correct any mistakes then mark as reviewed.',
        }),
        ('OCR text', {'fields': ('raw_ocr_text',), 'classes': ('collapse',)}),
        ('Review', {'fields': ('is_processed', 'is_doctor_reviewed', 'reviewed_by', 'reviewed_at')}),
    )

    def source_badge(self, obj):
        color = '#185FA5' if obj.source == TrainingReport.Source.USER_UPLOAD else '#0F6E56'
        label = 'User upload' if obj.source == TrainingReport.Source.USER_UPLOAD else 'Admin'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px">{}</span>', color, label)
    source_badge.short_description = 'Source'

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id: obj.uploaded_by = request.user
        if not change: obj.source = TrainingReport.Source.ADMIN
        super().save_model(request, obj, form, change)
        if not obj.is_processed and obj.file:
            ocr_training_report.delay(str(obj.id))

    @admin.action(description='Mark selected as doctor-reviewed')
    def mark_doctor_reviewed(self, request, queryset):
        updated = queryset.update(is_doctor_reviewed=True,
                                  reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f'{updated} records marked as reviewed.', messages.SUCCESS)

    @admin.action(description='Re-run OCR on selected')
    def run_ocr_on_selected(self, request, queryset):
        for tr in queryset: ocr_training_report.delay(str(tr.id))
        self.message_user(request, f'OCR queued for {queryset.count()} reports.', messages.SUCCESS)


@admin.register(FineTuningJob)
class FineTuningJobAdmin(admin.ModelAdmin):
    list_display  = ('id', 'status', 'samples_used', 'started_at', 'completed_at')
    list_filter   = ('status',)
    readonly_fields = ('id', 'status', 'triggered_by', 'samples_used',
                       'output_path', 'logs', 'started_at', 'completed_at', 'created_at')
    actions = ['start_finetuning']

    def save_model(self, request, obj, form, change):
        if not obj.triggered_by_id: obj.triggered_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Start fine-tuning for selected jobs')
    def start_finetuning(self, request, queryset):
        count = 0
        for job in queryset.filter(status__in=['pending', 'failed']):
            trigger_finetuning.delay(str(job.id))
            count += 1
        self.message_user(request, f'Fine-tuning started for {count} job(s).', messages.SUCCESS)


@admin.register(AutoTrainingConfig)
class AutoTrainingConfigAdmin(admin.ModelAdmin):
    list_display  = ('auto_training_enabled', 'new_samples_threshold',
                     'include_unreviewed', 'unreviewed_weight', 'last_auto_trigger_at')
    readonly_fields = ('last_auto_trigger_at', 'samples_at_last_trigger', 'updated_at')

    def has_add_permission(self, request):
        return not AutoTrainingConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False