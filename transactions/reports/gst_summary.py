from django.db.models import Sum
from django.utils.timezone import now
from transactions.models import GSTLedger


def get_monthly_gst_summary(year, month):
    qs = GSTLedger.objects.filter(
        created_at__year=year,
        created_at__month=month
    )

    taxable_value = qs.aggregate(
        total=Sum("transaction_fee__fee_amount")
    )["total"] or 0

    gst_total = qs.aggregate(
        total=Sum("gst_amount")
    )["total"] or 0

    return {
        "month": f"{year}-{month:02d}",
        "taxable_value": taxable_value,
        "gst_payable": gst_total,
        "total_tax": gst_total,
    }



def get_gst_summary_for_period(start_date, end_date):
    qs = GSTLedger.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )

    taxable_value = qs.aggregate(
        total=Sum("transaction_fee__fee_amount")
    )["total"] or 0

    gst_total = qs.aggregate(
        total=Sum("gst_amount")
    )["total"] or 0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "taxable_value": taxable_value,
        "gst_payable": gst_total,
        "total_tax": gst_total,
    }   

# ================================================================================
