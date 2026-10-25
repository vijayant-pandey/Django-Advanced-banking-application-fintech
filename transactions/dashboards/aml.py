from django.db.models import Count
from django.utils.timezone import now
from transactions.models import AMLAlert

def aml_alerts_today():
    today = now().date()
    return (
        AMLAlert.objects
        .filter(created_at__date=today)
        .count()
    )

def aml_by_type():
    return (
        AMLAlert.objects
        .values('alert_type')
        .annotate(count=Count('id'))
    )

def aml_resolved_vs_pending():
    return {
        "resolved": AMLAlert.objects.filter(is_resolved=True).count(),
        "pending": AMLAlert.objects.filter(is_resolved=False).count(),
    }
