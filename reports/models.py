import uuid
from django.db import models
from django.conf import settings


def report_upload_path(instance, filename):
    return f'reports/{instance.uploaded_by.id}/{uuid.uuid4()}_{filename}'


class LabReport(models.Model):
    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED  = 'completed',  'Completed'
        FAILED     = 'failed',     'Failed'

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by    = models.ForeignKey(settings.AUTH_USER_MODEL,
                                       on_delete=models.CASCADE, related_name='reports')
    file           = models.FileField(upload_to=report_upload_path)
    file_type      = models.CharField(max_length=10, blank=True)
    original_name  = models.CharField(max_length=255, blank=True)
    status         = models.CharField(max_length=15, choices=Status.choices,
                                      default=Status.PENDING)
    celery_task_id = models.CharField(max_length=255, blank=True)
    uploaded_at    = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Report {self.id} — {self.uploaded_by.username} [{self.status}]'


class AnalysisResult(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report              = models.OneToOneField(LabReport, on_delete=models.CASCADE,
                                               related_name='result')
    raw_text            = models.TextField(blank=True)
    extracted_values    = models.JSONField(default=dict)
    flagged_items       = models.JSONField(default=list)
    summary             = models.TextField(blank=True)
    conditions_detected = models.JSONField(default=list)
    severity            = models.CharField(
        max_length=10,
        choices=[('normal','Normal'),('mild','Mild'),('moderate','Moderate'),('severe','Severe')],
        default='normal',
    )
    pdf_report = models.FileField(upload_to='output_reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Result for report {self.report_id}'