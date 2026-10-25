from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from transactions.dashboards.fx import *
from transactions.dashboards.aml import *
from transactions.dashboards.exposure import *
from django.http import HttpResponse

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils.timezone import now
from django.db.models import Sum, Count

from transactions.models import (
    Transaction,
    TransactionFee,
    AMLAlert,
    GSTLedger,
)
from accounts.models import Wallet
from django.db.models.functions import TruncMonth

from transactions.models import GSTLedger


@staff_member_required
def admin_dashboard(request):
    today = now().date()

    # ================= FX INCOME =================
    fx_daily = (
        TransactionFee.objects
        .filter(created_at__date=today, reason="FX Spread")
        .aggregate(total=Sum("inr_equivalent"))["total"] or 0
    )

    fx_monthly = (
        TransactionFee.objects
        .filter(
            created_at__year=today.year,
            created_at__month=today.month,
            reason="FX Spread"
        )
        .aggregate(total=Sum("inr_equivalent"))["total"] or 0
    )

    fx_by_currency_qs = (
        TransactionFee.objects
        .filter(reason="FX Spread")
        .values("currency__code")
        .annotate(total=Sum("inr_equivalent"))
        .order_by("-total")
    )

    fx_labels = [row["currency__code"] for row in fx_by_currency_qs]
    fx_values = [float(row["total"]) for row in fx_by_currency_qs]

    # ================= AML =================
    aml_today = AMLAlert.objects.filter(created_at__date=today).count()

    aml_type_qs = (
        AMLAlert.objects
        .values("alert_type")
        .annotate(count=Count("id"))
    )

    aml_type_labels = [row["alert_type"] for row in aml_type_qs]
    aml_type_values = [row["count"] for row in aml_type_qs]

    aml_status_qs = (
        AMLAlert.objects
        .values("is_resolved")
        .annotate(count=Count("id"))
    )

    aml_status_labels = ["Resolved", "Pending"]
    aml_status_values = [
        next((r["count"] for r in aml_status_qs if r["is_resolved"]), 0),
        next((r["count"] for r in aml_status_qs if not r["is_resolved"]), 0),
    ]

    # ================= CURRENCY EXPOSURE =================
    exposure_qs = (
        Wallet.objects
        .values("currency__code")
        .annotate(total=Sum("balance"))
        .order_by("-total")
    )

    exposure_labels = [row["currency__code"] for row in exposure_qs]
    exposure_values = [float(row["total"]) for row in exposure_qs]

    # ================= TRANSACTION VOLUME (NEW) =================

    # Daily INR-normalized volume
    tx_daily_qs = (
        Transaction.objects
        .values("created_at__date")
        .annotate(total=Sum("inr_equivalent"))
        .order_by("created_at__date")
    )

    tx_daily_labels = [
        row["created_at__date"].strftime("%Y-%m-%d")
        for row in tx_daily_qs
    ]
    tx_daily_values = [
        float(row["total"] or 0)
        for row in tx_daily_qs
    ]

    # Deposit vs Withdraw count
    tx_type_qs = (
        Transaction.objects
        .values("transaction_type")
        .annotate(count=Count("id"))
    )

    tx_type_labels = [row["transaction_type"] for row in tx_type_qs]
    tx_type_values = [row["count"] for row in tx_type_qs]

    # Currency-wise INR volume
    tx_currency_qs = (
        Transaction.objects
        .values("currency__code")
        .annotate(total=Sum("inr_equivalent"))
        .order_by("-total")
    )

    tx_currency_labels = [
        row["currency__code"] or "UNKNOWN"
        for row in tx_currency_qs
    ]
    tx_currency_values = [
        float(row["total"] or 0)
        for row in tx_currency_qs
    ]

    # GST
    gst_monthly_qs = (
        GSTLedger.objects
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("gst_amount"))
        .order_by("month")
    )

    gst_month_labels = [
        row["month"].strftime("%b %Y") for row in gst_monthly_qs
    ]
    gst_month_values = [float(row["total"]) for row in gst_monthly_qs]


    # ================= FX + GST MONTHLY TREND =================

    fx_monthly_trend_qs = (
        TransactionFee.objects
        .filter(reason="FX Spread")
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("inr_equivalent"))
        .order_by("month")
    )

    fx_month_trend_labels = [
        row["month"].strftime("%b %Y") for row in fx_monthly_trend_qs
    ]

    fx_month_trend_values = [
        float(row["total"]) for row in fx_monthly_trend_qs
    ]







    context = {
        # FX
        "fx_daily": fx_daily,
        "fx_monthly": fx_monthly,
        "fx_labels": fx_labels,
        "fx_values": fx_values,

        # AML
        "aml_today": aml_today,
        "aml_type_labels": aml_type_labels,
        "aml_type_values": aml_type_values,
        "aml_status_labels": aml_status_labels,
        "aml_status_values": aml_status_values,
        
        # Exposure
        "exposure_labels": exposure_labels,
        "exposure_values": exposure_values,

        # Transactions
        "tx_daily_labels": tx_daily_labels,
        "tx_daily_values": tx_daily_values,
        "tx_type_labels": tx_type_labels,
        "tx_type_values": tx_type_values,
        "tx_currency_labels": tx_currency_labels,
        "tx_currency_values": tx_currency_values,

        # GST
        "gst_month_labels": gst_month_labels,
        "gst_month_values": gst_month_values,

        # FX + GST Monthly Trend
        "fx_month_trend_labels": fx_month_trend_labels,
        "fx_month_trend_values": fx_month_trend_values,
        
    }

    return render(request, "admin/dashboard.html", context)



