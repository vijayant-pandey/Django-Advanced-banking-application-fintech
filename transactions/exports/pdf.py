from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from django.http import HttpResponse
from django.utils.timezone import now
from reportlab.lib.styles import getSampleStyleSheet
from transactions.models import GSTLedger



# ================================================================================

def export_rbi_daily_report_pdf(queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="rbi_report_{now().date()}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(
        f"RBI Daily Transaction Report — {now().date()}",
        styles['Heading2']
    ))

    data = [[
        'Txn ID', 
        'Account', 
        'Type', 
        'Amount', 
        'Currency', 
        'INR Equivalent', 
        'Date'
    ]]

    for tx in queryset:
        data.append([
            tx.id,
            tx.account.account_number,
            tx.transaction_type,
            str(tx.amount),
            tx.currency.code if tx.currency else '',
            str(tx.inr_equivalent),
            tx.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
    ]))

    elements.append(table)
    doc.build(elements)

    return response

# ================================================================================

def export_aml_alerts_pdf(queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="aml_alerts_{now().date()}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(
        f"AML Alerts Report — {now().date()}",
        styles['Heading2']
    ))

    data = [[
        'Account', 'Alert Type', 'INR Amount', 'Resolved', 'Resolved by','Resolved at','Created At'
    ]]

    for alert in queryset:
        data.append([
            alert.account.account_number,
            alert.alert_type,
            str(alert.inr_amount or ''),
            "YES" if alert.is_resolved else "NO",
            alert.resolved_by.username if alert.resolved_by else '',
            alert.resolved_at.strftime('%Y-%m-%d %H:%M') if alert.resolved_at else '',
            alert.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
    ]))

    elements.append(table)
    doc.build(elements)

    return response


# ================================================================================


def export_fx_income_pdf(queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="fx_income_{now().date()}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(
        f"FX Income Report — {now().date()}",
        styles['Heading2']
    ))

    data = [[
        'Transaction ID', 'Fee Amount', 'Currency', 'INR Equivalent', 'Date'
    ]]

    for fee in queryset:
        data.append([
            fee.transaction.id,
            str(fee.fee_amount),
            fee.currency.code,
            str(fee.inr_equivalent),
            fee.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
    ]))

    elements.append(table)
    doc.build(elements)

    return response


# ================================================================================


def export_gst_report_pdf(queryset=None):
    if queryset is None:
        queryset = GSTLedger.objects.select_related("transaction_fee")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="gst_report_{now().date()}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("<b>GST Report (FX Fees)</b>", styles["Title"]))
    elements.append(Paragraph(f"Date: {now().date()}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    data = [[
        "Fee ID",
        "FX Fee (₹ - INR)",
        "GST %",
        "GST (₹ - INR)",
        "INR Equivalent (₹)",
        "Date",
    ]]


    for gst in queryset:
        data.append([
            gst.transaction_fee.id,
            f"{gst.transaction_fee.fee_amount:.2f}",
            f"{gst.gst_rate}%",
            f"{gst.gst_amount:.2f}",
            f"{gst.inr_equivalent:.2f}",
            gst.created_at.strftime("%Y-%m-%d"),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    elements.append(table)
    doc.build(elements)
    return response


# ================================================================================

# GST 3B Monthly Summary PDF Export

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.http import HttpResponse
from datetime import date
from transactions.reports.gst_summary import get_gst_summary_for_period
import calendar


def export_monthly_gst_pdf(year=None, month=None):
    today = now().date()
    year = year or today.year
    month = month or today.month

    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])

    summary = get_gst_summary_for_period(start_date, end_date)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="gst_summary_{year}_{month}.pdf"'
    )

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    elements.append(Paragraph("<b>GST Monthly Summary (GSTR-3B)</b>", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"Period: {summary['start_date']} to {summary['end_date']}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 12))

    table = Table([
        ["Particulars", "Amount (INR)"],
        ["Taxable Value", f"₹{summary['taxable_value']:,.2f}"],
        ["GST Payable (18%)", f"₹{summary['gst_payable']:,.2f}"],
        ["Total Tax", f"₹{summary['total_tax']:,.2f}"],
    ])

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        "Government compliant GST summary. Digitally generated.",
        styles["Italic"]
    ))

    doc.build(elements)
    return response

# ================================================================================
# GST + FX Combined Compliance Report PDF Export
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.http import HttpResponse
from django.utils.timezone import now
# from transactions.reports.fx_gst_summary import get_fx_gst_compliance_summary
from transactions.reports.fx_gst_compliance_summary import (get_fx_gst_compliance_summary)


def export_fx_gst_compliance_pdf(start_date, end_date):
    data = get_fx_gst_compliance_summary(start_date, end_date)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="fx_gst_compliance_{now().date()}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(
        "<b>FX + GST Compliance Summary</b>", styles["Title"]
    ))
    elements.append(Paragraph(
        f"Period: {data['period']}", styles["Normal"]
    ))
    elements.append(Paragraph(
        "For RBI / GST / Board Review", styles["Italic"]
    ))

    table = Table([
        ["Metric", "Amount (INR)"],
        ["FX Volume", data["fx_volume"]],
        ["FX Income", data["fx_income"]],
        ["GST Payable", data["gst_payable"]],
        ["Net FX Income", data["net_fx_income"]],
        ["AML Alerts", data["aml_total"]],
        ["AML Pending", data["aml_pending"]],
    ])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
    ]))

    elements.append(table)
    elements.append(Paragraph(
        f"Generated on: {data['generated_at']}", styles["Small"]
    ))

    doc.build(elements)
    return response
