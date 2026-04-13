import uuid
import django.db.models.deletion
import reports.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='LabReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to=reports.models.report_upload_path)),
                ('file_type', models.CharField(blank=True, max_length=10)),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(
                    choices=[('pending','Pending'),('processing','Processing'),
                             ('completed','Completed'),('failed','Failed')],
                    default='pending', max_length=15)),
                ('celery_task_id', models.CharField(blank=True, max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-uploaded_at']},
        ),
        migrations.CreateModel(
            name='AnalysisResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('raw_text', models.TextField(blank=True)),
                ('extracted_values', models.JSONField(default=dict)),
                ('flagged_items', models.JSONField(default=list)),
                ('summary', models.TextField(blank=True)),
                ('conditions_detected', models.JSONField(default=list)),
                ('severity', models.CharField(
                    choices=[('normal','Normal'),('mild','Mild'),
                             ('moderate','Moderate'),('severe','Severe')],
                    default='normal', max_length=10)),
                ('pdf_report', models.FileField(blank=True, null=True, upload_to='output_reports/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('report', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    related_name='result', to='reports.labreport')),
            ],
        ),
    ]