import uuid
import django.db.models.deletion
import training.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('reports', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='TrainingReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('source', models.CharField(choices=[('user_upload','User Upload (auto)'),('admin','Admin / Doctor (manual)')], default='admin', max_length=15)),
                ('file', models.FileField(upload_to=training.models.training_upload_path)),
                ('file_type', models.CharField(blank=True, max_length=10)),
                ('raw_ocr_text', models.TextField(blank=True)),
                ('correct_summary', models.TextField(blank=True)),
                ('correct_conditions', models.JSONField(default=list)),
                ('correct_severity', models.CharField(choices=[('normal','Normal'),('mild','Mild'),('moderate','Moderate'),('severe','Severe')], default='normal', max_length=10)),
                ('is_processed', models.BooleanField(default=False)),
                ('is_doctor_reviewed', models.BooleanField(default=False)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('lab_report', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='training_entry', to='reports.labreport')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_training_reports', to=settings.AUTH_USER_MODEL)),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='training_uploads', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-uploaded_at']},
        ),
        migrations.CreateModel(
            name='FineTuningJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending','Pending'),('running','Running'),('completed','Completed'),('failed','Failed')], default='pending', max_length=15)),
                ('base_model', models.CharField(default='google/flan-t5-base', max_length=200)),
                ('samples_used', models.IntegerField(default=0)),
                ('output_path', models.CharField(blank=True, max_length=500)),
                ('logs', models.TextField(blank=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('triggered_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='finetuning_jobs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AutoTrainingConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('auto_training_enabled', models.BooleanField(default=True)),
                ('new_samples_threshold', models.IntegerField(default=50)),
                ('include_unreviewed', models.BooleanField(default=True)),
                ('unreviewed_weight', models.FloatField(default=0.5)),
                ('last_auto_trigger_at', models.DateTimeField(blank=True, null=True)),
                ('samples_at_last_trigger', models.IntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Auto-training config', 'verbose_name_plural': 'Auto-training config'},
        ),
    ]