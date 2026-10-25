import csv
from django.http import HttpResponse
from transactions.models import AMLAlert
from transactions.models import TransactionFee
from django.utils.timezone import now
from transactions.models import Transaction


def export_aml_alerts_csv(queryset=None):
    if queryset is None:
        queryset = AMLAlert.objects.all()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="aml_alerts_{now().date()}.csv"'
    )


    writer = csv.writer(response)
    writer.writerow([
        'Account Number',
        'Alert Type',
        'INR Amount',
        'Is Resolved',
        'Resolved By',
        'Resolved At',
        'Created At'
    ])

    for alert in queryset:
        writer.writerow([
            alert.account.account_number,
            alert.alert_type,
            alert.inr_amount or '',
            alert.is_resolved,
            alert.resolved_by.username if alert.resolved_by else '',
            alert.resolved_at,
            alert.created_at,
        ])

    return response
# ---------------------------------------------------------------------------------------




# ---------------- RBI DAILY REPORT EXPORT ---------------- #

# def export_rbi_daily_report_csv(report_date=None):
#     if report_date is None:
#         report_date = now().date()

#     qs = Transaction.objects.all().order_by('-created_at')

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = (
#         f'attachment; filename="rbi_daily_report_{report_date}.csv"'
#     )

#     writer = csv.writer(response)
#     writer.writerow([
#         'Transaction ID',
#         'Account Number',
#         'Transaction Type',
#         'Amount',
#         'Currency',
#         'INR Equivalent',
#         'Date Time'
#     ])

#     for tx in qs:
#         writer.writerow([
#             tx.id,
#             tx.account.account_number,
#             tx.transaction_type,
#             tx.amount,
#             tx.currency.code if tx.currency else '',
#             tx.inr_equivalent,
#             tx.created_at,
#         ])

#     return response



def export_rbi_daily_report_csv(queryset=None):
    if queryset is None:
        queryset = Transaction.objects.all().order_by('-created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="rbi_transaction_report_{now().date()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID',
        'Account Number',
        'Transaction Type',
        'Amount',
        'Currency',
        'INR Equivalent',
        'Date Time'
    ])

    for tx in queryset:
        writer.writerow([
            tx.id,
            tx.account.account_number,
            tx.transaction_type,
            tx.amount,
            tx.currency.code if tx.currency else '',
            tx.inr_equivalent,
            tx.created_at,
        ])

    return response
# ---------------------------------------------------------------------------------------




# ---------------- FX INCOME REPORT EXPORT ---------------- #

# def export_fx_income_csv(report_date=None):
#     if report_date is None:
#         report_date = now().date()

#     qs = TransactionFee.objects.filter(
#         # created_at__date=report_date,
#         reason="FX Spread"
#     )

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = (
#         f'attachment; filename="fx_income_{report_date}.csv"'
#     )

#     writer = csv.writer(response)
#     writer.writerow([
#         'Transaction ID',
#         'Fee Amount',
#         'Currency',
#         'INR Equivalent',
#         'Date'
#     ])

#     for fee in qs:
#         writer.writerow([
#             fee.transaction.id,
#             fee.fee_amount,
#             fee.currency.code,
#             fee.inr_equivalent,
#             fee.created_at,
#         ])

#     return response


def export_fx_income_csv(queryset=None):
    if queryset is None:
        queryset = TransactionFee.objects.filter(reason="FX Spread")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="fx_income_{now().date()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Transaction ID',
        'Fee Amount',
        'Currency',
        'INR Equivalent',
        'Date'
    ])

    for fee in queryset:
        writer.writerow([
            fee.transaction.id,
            fee.fee_amount,
            fee.currency.code,
            fee.inr_equivalent,
            fee.created_at,
        ])

    return response
# ---------------------------------------------------------------------------------------