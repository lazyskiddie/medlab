from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import LabReport, AnalysisResult


class AnalysisResultInline(admin.StackedInline):
    model       = AnalysisResult
    extra       = 0
    can_delete  = False
    readonly_fields = ('severity_badge', 'summary', 'conditions_list',
                       'flagged_count', 'pdf_report_link', 'created_at')
    fields = ('severity_badge', 'summary', 'conditions_list',
              'flagged_count', 'pdf_report_link', 'created_at')

    def severity_badge(self, obj):
        colors = {'normal': ('#0F6E56','#E1F5EE'), 'mild': ('#854F0B','#FAEEDA'),
                  'moderate': ('#993C1D','#FAECE7'), 'severe': ('#A32D2D','#FCEBEB')}
        fg, bg = colors.get(obj.severity, ('#333','#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;'
            'border-radius:4px;font-weight:600;font-size:12px">{}</span>',
            bg, fg, obj.severity.upper())
    severity_badge.short_description = 'Severity'

    def conditions_list(self, obj):
        if not obj.conditions_detected: return '—'
        items = ''.join(f'<li>{c["name"]} ({c.get("confidence","?")})</li>'
                        for c in obj.conditions_detected)
        return format_html('<ul style="margin:0;padding-left:18px">{}</ul>', items)
    conditions_list.short_description = 'Conditions'

    def flagged_count(self, obj):
        abnormal = sum(1 for f in obj.flagged_items if f.get('status') != 'normal')
        critical = sum(1 for f in obj.flagged_items if f.get('is_critical'))
        return format_html('{} abnormal{}', abnormal,
                           format_html(', <span style="color:#A32D2D">{} critical</span>', critical)
                           if critical else '')
    flagged_count.short_description = 'Flagged'

    def pdf_report_link(self, obj):
        if obj.pdf_report:
            return format_html('<a href="{}" target="_blank">Download PDF</a>', obj.pdf_report.url)
        return '—'
    pdf_report_link.short_description = 'PDF'


@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    list_display  = ('short_id', 'uploaded_by', 'file_type', 'status_badge',
                     'in_training_set', 'uploaded_at', 'file_link')
    list_filter   = ('status', 'file_type')
    search_fields = ('uploaded_by__username', 'uploaded_by__email')
    readonly_fields = ('id', 'celery_task_id', 'uploaded_at', 'updated_at', 'training_entry_link')
    inlines = [AnalysisResultInline]
    actions = ['retrigger_analysis']
    ordering = ('-uploaded_at',)

    fieldsets = (
        ('Report info', {'fields': ('id', 'uploaded_by', 'file', 'file_type',
                                    'original_name', 'status', 'celery_task_id')}),
        ('Training', {'fields': ('training_entry_link',)}),
        ('Timestamps', {'fields': ('uploaded_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def short_id(self, obj):
        return str(obj.id)[:8] + '…'
    short_id.short_description = 'ID'

    def status_badge(self, obj):
        colors = {'pending': ('#888780','#F1EFE8'), 'processing': ('#185FA5','#E6F1FB'),
                  'completed': ('#0F6E56','#E1F5EE'), 'failed': ('#A32D2D','#FCEBEB')}
        fg, bg = colors.get(obj.status, ('#333','#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:500">{}</span>',
            bg, fg, obj.status.upper())
    status_badge.short_description = 'Status'

    def in_training_set(self, obj):
        try:
            entry = obj.training_entry
            if entry.is_doctor_reviewed:
                return format_html('<span style="color:#0F6E56;font-weight:500">✓ Reviewed</span>')
            return format_html('<span style="color:#185FA5">In dataset</span>')
        except Exception:
            return format_html('<span style="color:#D3D1C7">—</span>')
    in_training_set.short_description = 'Training'

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View</a>', obj.file.url)
        return '—'
    file_link.short_description = 'File'

    def training_entry_link(self, obj):
        try:
            entry = obj.training_entry
            url   = f'/admin/training/trainingreport/{entry.id}/change/'
            reviewed = ' (reviewed ✓)' if entry.is_doctor_reviewed else ' (pending review)'
            return format_html('<a href="{}">View training record{}</a>', url, reviewed)
        except Exception:
            return 'Not yet seeded.'
    training_entry_link.short_description = 'Training entry'

    @admin.action(description='Re-run analysis on selected reports')
    def retrigger_analysis(self, request, queryset):
        from analysis.tasks import run_analysis_pipeline
        count = 0
        for report in queryset:
            report.status = LabReport.Status.PENDING
            report.save(update_fields=['status'])
            task = run_analysis_pipeline.delay(str(report.id))
            report.celery_task_id = task.id
            report.save(update_fields=['celery_task_id'])
            count += 1
        self.message_user(request, f'Re-triggered {count} report(s).', messages.SUCCESS)


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display  = ('short_id', 'report', 'severity', 'created_at')
    list_filter   = ('severity',)
    readonly_fields = ('id', 'report', 'raw_text', 'extracted_values',
                       'flagged_items', 'conditions_detected', 'created_at')
    search_fields = ('report__id',)

    def short_id(self, obj):
        return str(obj.id)[:8] + '…'
    short_id.short_description = 'ID'