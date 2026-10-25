from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    ACTION_TYPES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('TRANSFER', 'Transfer'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('REVERSAL', 'Reversal'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES
    )

    description = models.TextField()

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} - {self.created_at}"
