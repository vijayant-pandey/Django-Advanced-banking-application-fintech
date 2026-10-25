from .models import AuditLog

def log_action(user, action_type, description, ip_address=None):
    AuditLog.objects.create(
        user=user,
        action_type=action_type,
        description=description,
        ip_address=ip_address
    )
