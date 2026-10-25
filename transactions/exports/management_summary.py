from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.http import HttpResponse
from django.utils.timezone import now
from django.db.models import Sum

from transactions.models import Transaction, TransactionFee, AMLAlert


def export_management_summary_pdf():
    today = now().date()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="management_summary_{today}.pdf"'
    )

    # ================= STYLES (DEFINE ONCE) =================
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            spaceAfter=6,
        )
    )

    # ================= DOCUMENT =================
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    # ================= HEADER =================
    elements.append(Paragraph(
        "Bank Operations Summary Report",
        styles["Title"]
    ))
    elements.append(Paragraph(
        f"Date: {today}", styles["Normal"]
    ))
    elements.append(Paragraph(
        "For Board / RBI Inspection",
        styles["Italic"]
    ))
    elements.append(Spacer(1, 12))

    # ================= METRICS =================
    total_txn = Transaction.objects.count()

    total_volume = (
        Transaction.objects.aggregate(
            total=Sum("inr_equivalent")
        )["total"] or 0
    )

    fx_income_today = (
        TransactionFee.objects.filter(
            reason="FX Spread",
            created_at__date=today
        ).aggregate(total=Sum("inr_equivalent"))["total"] or 0
    )

    fx_income_month = (
        TransactionFee.objects.filter(
            reason="FX Spread",
            created_at__year=today.year,
            created_at__month=today.month
        ).aggregate(total=Sum("inr_equivalent"))["total"] or 0
    )

    aml_total = AMLAlert.objects.count()
    aml_pending = AMLAlert.objects.filter(is_resolved=False).count()

    summary_table = Table([
        ["Metric", "Value"],
        ["Total Transactions", total_txn],
        ["Total Volume (INR)", f"₹{total_volume:,.2f}"],
        ["FX Income Today", f"₹{fx_income_today:,.2f}"],
        ["FX Income This Month", f"₹{fx_income_month:,.2f}"],
        ["AML Alerts (Total)", aml_total],
        ["AML Alerts (Pending)", aml_pending],
    ], colWidths=[220, 220])

    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    elements.append(Paragraph(
        "Key Metrics",
        styles["Heading2"]
    ))
    elements.append(summary_table)

    # ================= FOOTER =================
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        f"Generated on: {now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["Small"]
    ))
    elements.append(Paragraph(
        "Digitally generated report – no signature required.",
        styles["Small"]
    ))

    doc.build(elements)
    return response
