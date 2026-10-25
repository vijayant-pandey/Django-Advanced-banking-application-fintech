from django.core.management.base import BaseCommand
from django.utils.timezone import now
from transactions.reports.gst_summary import get_monthly_gst_summary
from audit.utils import log_action
from datetime import date
from transactions.reports.fx_gst_compliance_summary import get_fx_gst_compliance_summary

class Command(BaseCommand):
    help = "Generate monthly GST (GSTR-3B) summary"

    def handle(self, *args, **options):
        today = now().date()

        # Previous month calender logic
        year = today.year
        month = today.month - 1

        if month == 0:
            month = 12
            year -= 1
        
        start_date = date(year, month, 1)

        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)


        # -------------------------------
        # GST SUMMARY (GSTR-3B)
        # -------------------------------
        gst = get_monthly_gst_summary(year, month)

        # -------------------------------
        # FX + GST COMPLIANCE SUMMARY
        # -------------------------------
        fx_gst = get_fx_gst_compliance_summary(
            start_date=start_date,
            end_date=end_date
        )

        # -------------------------------
        # OUTPUT
        # -------------------------------
        self.stdout.write(self.style.SUCCESS(
            f"FX + GST Compliance Summary ({gst['month']})"
        ))
        
        self.stdout.write(f"FX Volume: ₹{fx_gst['fx_volume']}")
        self.stdout.write(f"FX Income: ₹{fx_gst['fx_income']}")
        self.stdout.write(f"GST Payable: ₹{fx_gst['gst_payable']}")
        self.stdout.write(f"Net FX Income: ₹{fx_gst['net_fx_income']}")

        # summary = get_monthly_gst_summary(year, month)

        # self.stdout.write(self.style.SUCCESS(
        #     f"GST Summary for {summary['month']}"
        # ))
        # self.stdout.write(f"Taxable Value: ₹{summary['taxable_value']}")
        # self.stdout.write(f"GST Payable: ₹{summary['gst_payable']}")

        # -------------------------------
        # AUDIT LOG (CRITICAL)
        # -------------------------------
        log_action(
            user=None,
            action_type="MONTH_END_COMPLIANCE_GST_REPORT",
            description=(
                f"Month-end FX + GST generated for {gst['month']} | "
                f"FX ₹{fx_gst['fx_income']} | "
                f"GST ₹{fx_gst['gst_payable']} | "
                f"Net ₹{fx_gst['net_fx_income']}"
            )
        )
