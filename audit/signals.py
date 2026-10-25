from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from audit.utils import log_action

@receiver(post_save)
def audit_model_save(sender, instance, created, **kwargs):
    if sender.__name__ in ['BankAccount', 'TransferRequest']:
        action = 'CREATE' if created else 'UPDATE'
        log_action(
            user=None,
            action_type=action,
            description=f'{sender.__name__} {action}: ID {instance.id}'
        )
