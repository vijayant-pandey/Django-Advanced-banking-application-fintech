from openpyxl import Workbook
from django.http import HttpResponse
from django.utils.timezone import now
from transactions.models import Transaction
from transactions.models import AMLAlert
from transactions.models import TransactionFee
from transactions.models import GSTLedger




# ==========================================================================================



def export_rbi_daily_report_excel(queryset=None):
    if queryset is None:
        queryset = Transaction.objects.all().order_by('-created_at')

    wb = Workbook()
    ws = wb.active
    ws.title = "RBI Transactions"

    ws.append([
        'Transaction ID',
        'Account Number',
        'Transaction Type',
        'Amount',
        'Currency',
        'INR Equivalent',
        'Date Time'
    ])

    for tx in queryset:
        ws.append([
            tx.id,
            tx.account.account_number,
            tx.transaction_type,
            float(tx.amount),
            tx.currency.code if tx.currency else '',
            float(tx.inr_equivalent) if tx.inr_equivalent else '',
            tx.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="rbi_transactions_{now().date()}.xlsx"'
    )

    wb.save(response)
    return response
# ==========================================================================================


def export_aml_alerts_excel(queryset=None):
    if queryset is None:
        queryset = AMLAlert.objects.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "AML Alerts"

    ws.append([
        'Account Number',
        'Alert Type',
        'INR Amount',
        'Is Resolved',
        'Resolved By',
        'Resolved At',
        'Created At'
    ])

    for alert in queryset:
        ws.append([
            alert.account.account_number,
            alert.alert_type,
            float(alert.inr_amount) if alert.inr_amount else '',
            "YES" if alert.is_resolved else "NO",
            alert.resolved_by.username if alert.resolved_by else '',
            alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else '',
            alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="aml_alerts_{now().date()}.xlsx"'
    )

    wb.save(response)
    return response

# ==========================================================================================


def export_fx_income_excel(queryset=None):
    if queryset is None:
        queryset = TransactionFee.objects.filter(reason="FX Spread")

    wb = Workbook()
    ws = wb.active
    ws.title = "FX Income"

    ws.append([
        'Transaction ID',
        'Fee Amount',
        'Currency',
        'INR Equivalent',
        'Date'
    ])

    for fee in queryset:
        ws.append([
            fee.transaction.id,
            float(fee.fee_amount),
            fee.currency.code,
            float(fee.inr_equivalent),
            fee.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="fx_income_{now().date()}.xlsx"'
    )

    wb.save(response)
    return response



# ==========================================================================================

def export_gst_report_excel(queryset=None):
    if queryset is None:
        queryset = GSTLedger.objects.select_related("transaction_fee")

    wb = Workbook()
    ws = wb.active
    ws.title = "GST Report"

    # Header
    ws.append([
        "Transaction Fee ID",
        "FX Fee Amount (INR)",
        "GST Rate (%)",
        "GST Amount (INR)",
        "INR Equivalent",
        "Date",
    ])

    for gst in queryset:
        ws.append([
            gst.transaction_fee.id,
            float(gst.transaction_fee.fee_amount),
            float(gst.gst_rate),
            float(gst.gst_amount),
            float(gst.inr_equivalent),
            gst.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="gst_report_{now().date()}.xlsx"'
    )

    wb.save(response)
    return response

# ==========================================================================================



# GST 3B Monthly Summary Excel Export
from openpyxl import Workbook
from django.http import HttpResponse
from django.utils.timezone import now
from transactions.reports.gst_summary import get_gst_summary_for_period
from datetime import date
import calendar


def export_monthly_gst_excel(year=None, month=None):
    today = now().date()

    year = year or today.year
    month = month or today.month

    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])

    summary = get_gst_summary_for_period(start_date, end_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "GST Summary (GSTR-3B)"

    ws.append(["GST Monthly Summary"])
    ws.append([f"Period: {summary['start_date']} to {summary['end_date']}"])
    ws.append([])

    ws.append(["Particulars", "Amount (INR)"])
    ws.append(["Taxable Value", float(summary["taxable_value"])])
    ws.append(["GST Payable (18%)", float(summary["gst_payable"])])
    ws.append(["Total Tax", float(summary["total_tax"])])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="gst_summary_{year}_{month}.xlsx"'
    )

    wb.save(response)
    return response
# ==========================================================================================


#  GST + FX Combined Compliance Report Excel Export
from openpyxl import Workbook
from django.http import HttpResponse
from django.utils.timezone import now
# from transactions.reports.fx_gst_summary import get_fx_gst_compliance_summary
from transactions.reports.fx_gst_compliance_summary import (get_fx_gst_compliance_summary)


def export_fx_gst_compliance_excel(start_date, end_date):
    data = get_fx_gst_compliance_summary(start_date, end_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "FX + GST Compliance"

    ws.append(["Metric", "Amount (INR)"])
    ws.append(["FX Volume", data["fx_volume"]])
    ws.append(["FX Income", data["fx_income"]])
    ws.append(["GST Payable", data["gst_payable"]])
    ws.append(["Net FX Income", data["net_fx_income"]])
    ws.append(["AML Alerts", data["aml_total"]])
    ws.append(["AML Pending", data["aml_pending"]])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="fx_gst_compliance_{now().date()}.xlsx"'
    )

    wb.save(response)
    return response

