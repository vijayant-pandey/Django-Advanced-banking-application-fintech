from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from audit.utils import log_action

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    log_action(
        user=user,
        action_type='LOGIN',
        description='User logged in',
        ip_address=request.META.get('REMOTE_ADDR')
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    log_action(
        user=user,
        action_type='LOGOUT',
        description='User logged out',
        ip_address=request.META.get('REMOTE_ADDR')
    )
