# from django.db.models import Sum
# from transactions.models import TransactionFee, GSTLedger


# def get_fx_gst_compliance_summary(year, month):
#     fx_qs = TransactionFee.objects.filter(
#         reason="FX Spread",
#         created_at__year=year,
#         created_at__month=month
#     )

#     gst_qs = GSTLedger.objects.filter(
#         created_at__year=year,
#         created_at__month=month
#     )

#     fx_income = fx_qs.aggregate(
#         total=Sum("inr_equivalent")
#     )["total"] or 0

#     gst_paid = gst_qs.aggregate(
#         total=Sum("gst_amount")
#     )["total"] or 0

#     return {
#         "period": f"{year}-{month:02d}",
#         "fx_income": fx_income,
#         "gst_paid": gst_paid,
#         "net_income": fx_income - gst_paid,
#         "tx_count": fx_qs.count(),
#     }




from django.db.models import Sum
from django.utils.timezone import now
from transactions.models import TransactionFee, GSTLedger, AMLAlert, Transaction


def get_fx_gst_compliance_summary(start_date, end_date):
    fx_income = (
        TransactionFee.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            reason="FX Spread"
        ).aggregate(total=Sum("inr_equivalent"))["total"] or 0
    )

    gst_total = (
        GSTLedger.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(total=Sum("inr_equivalent"))["total"] or 0
    )

    fx_volume = (
        Transaction.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(total=Sum("inr_equivalent"))["total"] or 0
    )

    aml_total = AMLAlert.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()

    aml_pending = AMLAlert.objects.filter(
        is_resolved=False,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()

    return {
        "period": f"{start_date} → {end_date}",
        "fx_volume": fx_volume,
        "fx_income": fx_income,
        "gst_payable": gst_total,
        "net_fx_income": fx_income - gst_total,
        "aml_total": aml_total,
        "aml_pending": aml_pending,
        "generated_at": now(),
    }
