from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Run all first-time setup steps for MedLab.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email',    default='admin@medlab.local')
        parser.add_argument('--password', default='admin1234')

    def handle(self, *args, **options):
        from django.core.management import call_command
        from pathlib import Path
        from django.conf import settings

        self.stdout.write('Running migrations...')
        call_command('migrate', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✓ Migrations done'))

        User     = get_user_model()
        username = options['username']
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username, email=options['email'],
                password=options['password'], role='admin',
            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ Superuser "{username}" created'))
        else:
            self.stdout.write(f'  ℹ Superuser "{username}" already exists')

        from training.models import AutoTrainingConfig
        cfg = AutoTrainingConfig.get()
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ AutoTrainingConfig ready (threshold={cfg.new_samples_threshold})'))

        dirs = [
            settings.MEDIA_ROOT, settings.MEDIA_ROOT / 'reports',
            settings.MEDIA_ROOT / 'training_data' / 'user_uploads',
            settings.MEDIA_ROOT / 'output_reports',
            settings.MODELS_DIR, settings.MODELS_DIR / 'ner',
            settings.MODELS_DIR / 'summarizer', Path(settings.BASE_DIR) / 'static',
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.SUCCESS('  ✓ Directories created'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('  MedLab setup complete!'))
        self.stdout.write(f'  Admin: http://localhost:8000/admin/  ({username} / {options["password"]})')
        self.stdout.write('  Next: python manage.py download_models')