from django.db.models import Sum
from django.utils.timezone import now
from transactions.models import TransactionFee

def fx_income_daily():
    today = now().date()
    return (
        TransactionFee.objects
        .filter(reason="FX Spread", created_at__date=today)
        .aggregate(total=Sum('inr_equivalent'))['total']
        or 0
    )

def fx_income_monthly():
    today = now()
    return (
        TransactionFee.objects
        .filter(
            reason="FX Spread",
            created_at__year=today.year,
            created_at__month=today.month
        )
        .aggregate(total=Sum('inr_equivalent'))['total']
        or 0
    )

def fx_income_by_currency():
    return (
        TransactionFee.objects
        .filter(reason="FX Spread")
        .values('currency__code')
        .annotate(total=Sum('inr_equivalent'))
        .order_by('-total')
    )
