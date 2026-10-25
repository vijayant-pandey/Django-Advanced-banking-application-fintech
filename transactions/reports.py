from datetime import date
from django.utils.timezone import localdate
from .models import Transaction
from django.utils.timezone import now
from django.db.models import Sum
from .models import Transaction
from django.db.models import Sum
from .models import TransactionFee

# def daily_transaction_report(report_date=None):
#     if report_date is None:
#         report_date = date.today()

#     return Transaction.objects.filter(
#         created_at__date=report_date
#     ).values(
#         'account__account_number',
#         'transaction_type',
#         'amount',
#         'currency__code',
#         'inr_equivalent',
#         'created_at'
#     )

def daily_transaction_report(report_date=None):
    if report_date is None:
        report_date = localdate()   # ✅ timezone-safe

    return Transaction.objects.filter(
        created_at__date=report_date
    ).values(
        'account__account_number',
        'transaction_type',
        'amount',
        'currency__code',
        'inr_equivalent',
        'created_at'
    )



def daily_bank_settlement_volume(report_date=None):
    if report_date is None:
        report_date = now().date()

    return Transaction.objects.filter(
        created_at__date=report_date
    ).aggregate(
        total_inr=Sum('inr_equivalent')
    )




def daily_fx_income_report(report_date=None):
    if report_date is None:
        report_date = now().date()

    return TransactionFee.objects.filter(
        reason="FX Spread",
        created_at__date=report_date
    ).aggregate(
        total_fx_income=Sum('inr_equivalent')
    )
