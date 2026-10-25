from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'action_type',
        'user',
        'description',
        'ip_address',
        'created_at',
    )
    list_filter = ('action_type', 'created_at')
    search_fields = ('description', 'user__username')

# if commented all the three defs then /admin/--> audit--> audit logs --> admin can delete the logs, which is not a good practice, as logs should never be deleted, it is a history of actions performed in the system.
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False