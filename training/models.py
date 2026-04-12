import uuid
from django.db import models
from django.conf import settings


def training_upload_path(instance, filename):
    return f'training_data/{uuid.uuid4()}_{filename}'


class TrainingReport(models.Model):
    class Source(models.TextChoices):
        USER_UPLOAD = 'user_upload', 'User Upload (auto)'
        ADMIN       = 'admin',       'Admin / Doctor (manual)'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='training_uploads')
    lab_report  = models.OneToOneField('reports.LabReport', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='training_entry')
    source      = models.CharField(max_length=15, choices=Source.choices, default=Source.ADMIN)
    file        = models.FileField(upload_to=training_upload_path)
    file_type   = models.CharField(max_length=10, blank=True)

    raw_ocr_text       = models.TextField(blank=True)
    correct_summary    = models.TextField(blank=True)
    correct_conditions = models.JSONField(default=list)
    correct_severity   = models.CharField(
        max_length=10,
        choices=[('normal','Normal'),('mild','Mild'),('moderate','Moderate'),('severe','Severe')],
        default='normal',
    )
    is_processed       = models.BooleanField(default=False)
    is_doctor_reviewed = models.BooleanField(default=False)
    uploaded_at        = models.DateTimeField(auto_now_add=True)
    reviewed_at        = models.DateTimeField(null=True, blank=True)
    reviewed_by        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name='reviewed_training_reports')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        reviewed = ' ✓' if self.is_doctor_reviewed else ''
        return f'TrainingReport [{self.source}]{reviewed} — {self.correct_severity}'


class FineTuningJob(models.Model):
    class JobStatus(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        RUNNING   = 'running',   'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED    = 'failed',    'Failed'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, related_name='finetuning_jobs')
    status       = models.CharField(max_length=15, choices=JobStatus.choices,
                                    default=JobStatus.PENDING)
    base_model   = models.CharField(max_length=200, default='google/flan-t5-base')
    samples_used = models.IntegerField(default=0)
    output_path  = models.CharField(max_length=500, blank=True)
    logs         = models.TextField(blank=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'FineTuningJob {self.id} [{self.status}]'


class AutoTrainingConfig(models.Model):
    auto_training_enabled   = models.BooleanField(default=True)
    new_samples_threshold   = models.IntegerField(default=50)
    include_unreviewed      = models.BooleanField(default=True)
    unreviewed_weight       = models.FloatField(default=0.5)
    last_auto_trigger_at    = models.DateTimeField(null=True, blank=True)
    samples_at_last_trigger = models.IntegerField(default=0)
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Auto-training config'
        verbose_name_plural = 'Auto-training config'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'AutoTrainingConfig [threshold={self.new_samples_threshold}]'