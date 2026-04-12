from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_auto_training_config(sender, **kwargs):
    if sender.name == 'training':
        try:
            from training.models import AutoTrainingConfig
            AutoTrainingConfig.get()
        except Exception:
            pass