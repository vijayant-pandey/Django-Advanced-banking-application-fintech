from django.db.models import Sum
from accounts.models import Wallet

def exposure_by_currency():
    return (
        Wallet.objects
        .values('currency__code')
        .annotate(total_balance=Sum('balance'))
        .order_by('-total_balance')
    )

def exposure_inr_normalized():
    return (
        Wallet.objects
        .values('currency__code')
        .annotate(total_inr=Sum('balance'))
    )
