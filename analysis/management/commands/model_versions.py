import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Manage local NLP model versions.'

    def add_arguments(self, parser):
        parser.add_argument('--activate', type=int, metavar='VERSION')
        parser.add_argument('--rollback', action='store_true')
        parser.add_argument('--info',     action='store_true')
        parser.add_argument('--snapshot', action='store_true')

    def handle(self, *args, **options):
        models_dir   = Path(settings.MODELS_DIR)
        versions_dir = models_dir / 'versions'
        active_link  = models_dir / 'summarizer_active'
        finetuned    = models_dir / 'summarizer_finetuned'
        versions_dir.mkdir(parents=True, exist_ok=True)

        if options['info']:
            if active_link.is_symlink():
                self.stdout.write(f'Active: {active_link.resolve()}')
            elif finetuned.exists():
                self.stdout.write(f'Using: {finetuned}')
            else:
                self.stdout.write('No fine-tuned model — using base model.')
            return

        if options['snapshot']:
            if not finetuned.exists():
                self.stdout.write(self.style.ERROR('No fine-tuned model found. Run a training job first.')); return
            existing = [int(p.name[1:]) for p in versions_dir.glob('v*') if p.name[1:].isdigit()]
            next_v   = max(existing, default=0) + 1
            dest     = versions_dir / f'v{next_v}'
            self.stdout.write(f'Copying to {dest} ...')
            shutil.copytree(finetuned, dest)
            if active_link.is_symlink() or active_link.exists(): active_link.unlink()
            active_link.symlink_to(dest)
            self.stdout.write(self.style.SUCCESS(f'✓ Saved as v{next_v} and set active.'))
            return

        if options['activate'] is not None:
            target = versions_dir / f'v{options["activate"]}'
            if not target.exists():
                self.stdout.write(self.style.ERROR(f'Version v{options["activate"]} not found.')); return
            if active_link.is_symlink() or active_link.exists(): active_link.unlink()
            active_link.symlink_to(target)
            self.stdout.write(self.style.SUCCESS(f'✓ Active set to v{options["activate"]}.'))
            return

        if options['rollback']:
            versions = sorted(versions_dir.glob('v*'),
                              key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0)
            if len(versions) < 2:
                self.stdout.write(self.style.ERROR('Need at least 2 versions to rollback.')); return
            prev = versions[-2]
            if active_link.is_symlink() or active_link.exists(): active_link.unlink()
            active_link.symlink_to(prev)
            self.stdout.write(self.style.SUCCESS(f'✓ Rolled back to {prev.name}.'))
            return

        # List
        versions = sorted(versions_dir.glob('v*'),
                          key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0)
        active   = active_link.resolve() if active_link.is_symlink() else None
        if not versions:
            self.stdout.write('No saved versions. Run --snapshot after a training job.')
        for v in versions:
            marker = ' ← active' if active and v.resolve() == active else ''
            self.stdout.write(f'  {v.name}{marker}  {v}')