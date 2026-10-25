from django.utils.timezone import localdate
from django.db.models import Sum
from decimal import Decimal

from .models import Transaction, AMLAlert

from datetime import timedelta
from django.utils.timezone import now



DAILY_LIMIT_INR = Decimal('1000000.00')  # ₹10L


def check_daily_limit(account):
    today = localdate()

    total = Transaction.objects.filter(
        account=account,
        created_at__date=today
    ).aggregate(
        total_inr=Sum('inr_equivalent')
    )['total_inr'] or Decimal('0.00')

    if total >= DAILY_LIMIT_INR:
        AMLAlert.objects.get_or_create(
            account=account,
            alert_type='DAILY_LIMIT',
            defaults={
                'inr_amount': total,
                'description': (
                    f'Daily transaction volume exceeded ₹10L. '
                    f'Total: ₹{total}'
                )
            }
        )




def check_rapid_transactions(account):
    last_10_min = now() - timedelta(minutes=10)

    count = Transaction.objects.filter(
        account=account,
        created_at__gte=last_10_min
    ).count()

    if count >= 5:
        AMLAlert.objects.get_or_create(
            account=account,
            alert_type='RAPID_TX',
            defaults={
                'description': (
                    f'{count} transactions within 10 minutes'
                )
            }
        )



# def check_suspicious_fx(account):
#     today = localdate()

#     fx_total = Transaction.objects.filter(
#         account=account,
#         currency__code__ne='INR',
#         created_at__date=today
#     ).aggregate(
#         total_fx=Sum('inr_equivalent')
#     )['total_fx'] or Decimal('0.00')

#     if fx_total >= Decimal('500000'):  # ₹5L FX exposure
#         AMLAlert.objects.get_or_create(
#             account=account,
#             alert_type='SUSPICIOUS_FX',
#             defaults={
#                 'inr_amount': fx_total,
#                 'description': (
#                     f'High FX activity detected. '
#                     f'INR equivalent ₹{fx_total}'
#                 )
#             }
#         )



def check_suspicious_fx(account):
    today = localdate()

    fx_total = Transaction.objects.filter(
        account=account,
        created_at__date=today
    ).exclude(
        currency__code='INR'
    ).aggregate(
        total_fx=Sum('inr_equivalent')
    )['total_fx'] or Decimal('0.00')

    if fx_total >= Decimal('500000'):  # ₹5L
        AMLAlert.objects.get_or_create(
            account=account,
            alert_type='SUSPICIOUS_FX',
            defaults={
                'inr_amount': fx_total,
                'description': (
                    f'High FX activity detected. '
                    f'INR equivalent ₹{fx_total}'
                )
            }
        )
 