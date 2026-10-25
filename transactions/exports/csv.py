import csv
from django.http import HttpResponse
from django.utils.timezone import now
from transactions.models import AMLAlert, Transaction, TransactionFee, GSTLedger


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



# def export_gst_report_csv(queryset=None):
#     if queryset is None:
#         queryset = GSTLedger.objects.all()

#     response = HttpResponse(content_type="text/csv")
#     response["Content-Disposition"] = (
#         f'attachment; filename="gst_report_{now().date()}.csv"'
#     )

#     writer = csv.writer(response)
#     writer.writerow([
#         "Transaction Fee ID",
#         "FX Fee Amount",
#         "GST Rate (%)",
#         "GST Amount",
#         "Date"
#     ])

#     for gst in queryset:
#         writer.writerow([
#             gst.transaction_fee.id,
#             gst.transaction_fee.fee_amount,
#             gst.gst_rate,
#             gst.gst_amount,
#             gst.created_at,
#         ])

#     return response



def export_gst_report_csv(queryset=None):
    if queryset is None:
        queryset = GSTLedger.objects.all()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="gst_report_{now().date()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        "Transaction Fee ID",
        "FX Fee Amount (INR)",
        "GST Rate (%)",
        "GST Amount (INR)",
        "INR Equivalent",
        "Date"
    ])

    for gst in queryset:
        writer.writerow([
            gst.transaction_fee.id,
            gst.transaction_fee.inr_equivalent,
            gst.gst_rate,
            gst.gst_amount,
            gst.inr_equivalent,
            gst.created_at,
        ])

    return response




# ==========================================================================================

#   GSTR-3B Monthly GST Summary CSV Export
import csv
from django.http import HttpResponse
from django.utils.timezone import now

from transactions.reports.gst_summary import get_monthly_gst_summary


def export_monthly_gst_csv(year=None, month=None):
    """
    GSTR-3B style MONTHLY GST CSV
    """

    today = now().date()
    year = year or today.year
    month = month or today.month

    summary = get_monthly_gst_summary(year, month)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="gst_gstr3b_{year}_{month:02d}.csv"'
    )

    writer = csv.writer(response)

    # Header
    writer.writerow([
        "Period",
        "Taxable Value (INR)",
        "GST Payable (18%)",
        "Total Tax (INR)"
    ])

    # Data row
    writer.writerow([
        summary["month"],
        summary["taxable_value"],
        summary["gst_payable"],
        summary["total_tax"],
    ])

    return response


# ==========================================================================================

# GST + FX Combined Compliance Report
# This is what RBI / Statutory Auditors / Big-4 love.

import csv
from django.http import HttpResponse
from django.utils.timezone import now
from transactions.reports.fx_gst_compliance_summary import (
    get_fx_gst_compliance_summary
)


# def export_fx_gst_compliance_csv(year=None, month=None):
#     today = now().date()
#     year = year or today.year
#     month = month or today.month

#     data = get_fx_gst_compliance_summary(year, month)

#     response = HttpResponse(content_type="text/csv")
#     response["Content-Disposition"] = (
#         f'attachment; filename="fx_gst_compliance_{data["period"]}.csv"'
#     )

#     writer = csv.writer(response)
#     writer.writerow([
#         "Period",
#         "FX Income (INR)",
#         "GST Paid (INR)",
#         "Net FX Income",
#         "FX Transactions"
#     ])

#     writer.writerow([
#         data["period"],
#         data["fx_income"],
#         data["gst_paid"],
#         data["net_income"],
#         data["tx_count"],
#     ])

#     return response



import csv
from django.http import HttpResponse
from django.utils.timezone import now
from transactions.reports.fx_gst_compliance_summary import (get_fx_gst_compliance_summary)

def export_fx_gst_compliance_csv(start_date, end_date):
    data = get_fx_gst_compliance_summary(start_date, end_date)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="fx_gst_compliance_{now().date()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["Metric", "Amount (INR)"])

    writer.writerow(["FX Volume", data["fx_volume"]])
    writer.writerow(["FX Income", data["fx_income"]])
    writer.writerow(["GST Payable", data["gst_payable"]])
    writer.writerow(["Net FX Income", data["net_fx_income"]])
    writer.writerow(["AML Alerts", data["aml_total"]])
    writer.writerow(["AML Pending", data["aml_pending"]])

    return response
