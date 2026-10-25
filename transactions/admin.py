from django.contrib import admin
from .models import Transaction
from .models import TransferRequest
from .services import approve_transfer, reject_transfer, settle_transfer
from .models import AMLAlert
from django.utils.timezone import now
from .models import TransactionFee, GSTLedger
from transactions.models import GSTLedger
from transactions.models import FXRateLock
from transactions.settlement_engine import create_upi_intent
from audit.utils import log_action
from transactions.admin_utils import expiry_badge, time_left


# from transactions.exports import export_aml_alerts_csv
# from transactions.exports import export_rbi_daily_report_csv
# from transactions.exports import export_fx_income_csv


from transactions.exports.csv import (

    export_rbi_daily_report_csv,
    export_aml_alerts_csv,
    export_fx_income_csv,

    # GST Report 
    export_gst_report_csv, 

    # GST - 3B Report 
    export_monthly_gst_csv,

    # Fx + GST Compliance Report
    export_fx_gst_compliance_csv,
    
)

from transactions.exports.pdf import ( 
    export_rbi_daily_report_pdf, 
    export_aml_alerts_pdf, 
    export_fx_income_pdf,

    #GST Report
    export_gst_report_pdf,

    # GST - 3B Report
    export_monthly_gst_pdf,

    # Fx + GST Compliance Report
    export_fx_gst_compliance_pdf,

)

from transactions.exports.excel import (
    export_rbi_daily_report_excel,
    export_aml_alerts_excel,
    export_fx_income_excel,

    # GST Report
    export_gst_report_excel,


    # GST - 3B Report
    export_monthly_gst_excel,

    # Fx + GST Compliance Report
    export_fx_gst_compliance_excel,

)

from transactions.exports.management_summary import (
    export_management_summary_pdf
)


from datetime import date
from transactions.settlement_engine import dispatch_settlement
from transactions.services_fx import create_fx_rate_lock
# ===============================================================================

@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'from_account',
        'to_account',
        'amount',
        'channel',
        'status',
        'reference_number',
        'neft_batch_id',
        'is_approved',
        'is_rejected',
        'created_at',
        'upi_intent_status',
        'upi_intent_expires_at',
        'upi_expiry_badge',
        'upi_time_left',


    )
    list_filter = ('is_approved', 'is_rejected')
    actions = ['approve_selected_transfers', 'reject_selected_transfers', 'approve_upi_intents', 'reject_upi_intents', 'approve_fx_rate', 'requote_fx']
    readonly_fields = ('from_account', 'to_account', 'amount', 'is_approved', 'is_rejected')

    def approve_selected_transfers(self, request, queryset):
    #  MAKER–CHECKER ENFORCEMENT
        if not request.user.is_staff:
            self.message_user(
                request,
                "You are not authorized to approve transfers.",
                level='error'
            )
            return

        for transfer in queryset:

            if transfer.is_approved or transfer.is_rejected:
                continue

            try:
                # 1️⃣ APPROVAL ONLY (Common for all)
                approve_transfer(
                    transfer=transfer,
                    performed_by=request.user
                )

                # 2️⃣ CHANNEL-WISE SETTLEMENT
                # 🚫 NEFT & UPI MUST NOT SETTLE HERE
                # if transfer.channel in ['INTERNAL', 'RTGS', 'IMPS', 'FX']:
                #     dispatch_settlement(
                #         transfer=transfer,
                #         performed_by=request.user
                #     )
                # inside approve_selected_transfers loop
                if transfer.channel == 'FX':
                    # 🔐 CREATE FX RATE LOCK HERE
                    create_fx_rate_lock(transfer)

                    transfer.status = 'PENDING'
                    transfer.save(update_fields=['status'])
                    # return

                    log_action(
                        user=request.user,
                        action_type='FX_RATE_LOCKED',
                        description=f"FX rate locked | Ref {transfer.reference_number}"
                    )
                    continue

                elif transfer.channel in ['INTERNAL', 'RTGS', 'IMPS']:
                    dispatch_settlement(
                        transfer=transfer,
                        performed_by=request.user
                    )
                elif transfer.channel == 'UPI':
                    # 🚨 CREATE INTENT HERE (ONLY HERE)
                    create_upi_intent(transfer)

            except ValueError as e:
                # ✅ SAFE ADMIN ERROR (NO CRASH)
                self.message_user(
                    request,
                    f"Transfer ID {transfer.id}: {str(e)}",
                    level='error'
                )
                # continue


    approve_selected_transfers.short_description = "Approve & Execute Transfer"

    def reject_selected_transfers(self, request, queryset):
        # 🔒 MAKER–CHECKER ENFORCEMENT
        if not request.user.is_staff:
            self.message_user(
                request,
                "You are not authorized to reject transfers.",
                level='error'
            )
            return
        
        for transfer in queryset:
            if not transfer.is_approved and not transfer.is_rejected:
                reject_transfer(
                    transfer=transfer,
                    performed_by=request.user,
                    reason="Rejected by admin"
                )

    reject_selected_transfers.short_description = "Reject Transfer"

    @admin.action(description="Approve UPI Intent")
    def approve_upi_intents(self, request, queryset):
        for transfer in queryset.filter(
            channel='UPI',
            status='PENDING',
            upi_intent_status='CREATED'
        ):
            # ⛔ BLOCK expired intents
            if (
                transfer.upi_intent_status == 'EXPIRED'
                or (transfer.upi_intent_expires_at and now() > transfer.upi_intent_expires_at)
            ):
                self.message_user(
                    request,
                    f"UPI intent expired for Ref {transfer.reference_number}",
                    level='error'
                )
                continue

            transfer.status = 'APPROVED'
            transfer.upi_intent_status = 'APPROVED'
            transfer.save(update_fields=['status', 'upi_intent_status'])

            log_action(
                user=request.user,
                action_type='UPI_INTENT_APPROVED',
                description=f"UPI intent approved | Ref {transfer.reference_number}"
            )

            # Settle Funds
            dispatch_settlement(
                transfer=transfer, 
                performed_by=request.user)


    @admin.action(description="Reject UPI Intent")
    def reject_upi_intents(self, request, queryset):
        queryset.filter(channel='UPI', status='PENDING').update(
            status='FAILED',
            upi_intent_status='REJECTED'
        )

    def upi_expiry_badge(self, obj):
        return expiry_badge(obj.upi_intent_expires_at)
    
    upi_expiry_badge.short_description = "UPI Status"
    upi_expiry_badge.admin_order_field = "upi_intent_expires_at"

    def upi_time_left(self, obj):
        return time_left(obj.upi_intent_expires_at)
    
    upi_time_left.short_description = "UPI Time Left"


    def get_queryset(self, request):
        qs = super().get_queryset(request)

        from django.utils.timezone import now

        expired = qs.filter(
            channel='UPI',
            status='PENDING',
            upi_intent_expires_at__lt=now()
        )

        for transfer in expired:
            transfer.status = 'FAILED'
            transfer.upi_intent_status = 'EXPIRED'
            transfer.save(update_fields=['status', 'upi_intent_status'])

        return qs

    # @admin.action(description="Requote FX Rate")
    # def requote_fx(self, request, queryset):
    #     for transfer in queryset.filter(channel='FX', status='FAILED'):
    #         transfer.fx_rate_lock.delete()
    #         transfer.status = 'INITIATED'
    #         transfer.save(update_fields=['status'])
    @admin.action(description="Requote FX Rate")
    def requote_fx(self, request, queryset):
        for transfer in queryset.filter(channel='FX', status='PENDING'):

            if not hasattr(transfer, 'fx_rate_lock'):
                continue

            # Delete old lock
            transfer.fx_rate_lock.delete()

            # Reset lifecycle
            transfer.status = 'INITIATED'
            transfer.is_approved = False
            transfer.reference_number = None
            transfer.save(update_fields=[
                'status',
                'is_approved',
                'reference_number'
            ])

            log_action(
                user=request.user,
                action_type='FX_REQUOTE',
                description=f"FX requote initiated | Transfer ID {transfer.id}"
            )




    @admin.action(description="Approve FX Rate (Confirm FX)")
    def approve_fx_rate(self, request, queryset):
        for transfer in queryset.filter(channel='FX', status='PENDING'):

            if not hasattr(transfer, 'fx_rate_lock'):
                self.message_user(
                    request,
                    f"No FX rate lock for Ref {transfer.reference_number}",
                    level='error'
                )
                continue

            lock = transfer.fx_rate_lock

            if lock.is_expired or now() > lock.expires_at:
                self.message_user(
                    request,
                    f"FX rate expired for Ref {transfer.reference_number}",
                    level='error'
                )
                continue

            transfer.status = 'APPROVED'
            transfer.save(update_fields=['status'])

            log_action(
                user=request.user,
                action_type='FX_RATE_APPROVED',
                description=f"FX rate approved | Ref {transfer.reference_number}"
            )

            # 🔥 NOW SETTLE
            dispatch_settlement(
                transfer,
                request.user
            )




# ===============================================================================

# @admin.register(FXRateLock)
# class FXRateLockAdmin(admin.ModelAdmin):
#     list_display = (
#         'transfer',
#         'from_currency',
#         'to_currency',
#         'rate',
#         'expires_at',
#         'is_expired',
#     )

@admin.register(FXRateLock)
class FXRateLockAdmin(admin.ModelAdmin):
    list_display = (
        'transfer_ref',
        'from_currency',
        'to_currency',
        'rate',
        'expires_at',
        # 'expiry_badge',
        'time_left',
    )

    readonly_fields = (
        'transfer',
        'from_currency',
        'to_currency',
        'rate',
        'expires_at',
    )

    def transfer_ref(self, obj):
        return obj.transfer.reference_number
    transfer_ref.short_description = "Transfer Ref"

    # def expiry_badge(self, obj):
    #     if obj.expires_at:
    #         return "❌ EXPIRED"
    #     return "✅ ACTIVE"
    # expiry_badge.short_description = "Status"

    def time_left(self, obj):
        remaining = obj.expires_at - now()
        if remaining.total_seconds() <= 0:
            return "Expired"
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        return f"{minutes}m {seconds}s"
    time_left.short_description = "Time Left"

# =============================================================

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'account',
        'transaction_type',
        'amount',
        'currency_display',
        'inr_equivalent',
        'mode',
        'channel',
        'reference_number',
        'balance_after_transaction',
        'created_at',
    )
    list_filter = ('transaction_type', 'currency', 'created_at')
    search_fields = ('account__account_number', 'transaction_type', 'amount',   'balance_after_transaction', 'created_at')
    actions = ['download_rbi_report', 'download_rbi_report_pdf', 'download_rbi_report_excel', 'download_management_summary']

    ordering = ('-created_at',)

    readonly_fields = (
        'account',
        'wallet',
        'transaction_type',
        'amount',
        'currency',
        'inr_equivalent',
        'balance_after_transaction',
        'created_at',
        'mode',
        'channel',
        'reference_number',
        'cheque_number',
    )

    def currency_display(self, obj):
        if obj.currency:
            return obj.currency.code
        return "-"

    currency_display.short_description = "Currency"

    # def channel(self, obj):
    #     return obj.channel or "-"
    # channel.short_description = "Channel"

    # def reference_number(self, obj):
    #     return obj.reference_number or "-"
    # reference_number.short_description = "Reference"



    @admin.action(description="Download RBI Daily Report (CSV)")
    def download_rbi_report(modeladmin, request, queryset):
        return export_rbi_daily_report_csv(queryset)
    

    @admin.action(description="Download RBI Report (PDF)")
    def download_rbi_report_pdf(modeladmin, request, queryset):
        return export_rbi_daily_report_pdf(queryset)
    
    @admin.action(description="Download RBI Report (Excel)")
    def download_rbi_report_excel(modeladmin, request, queryset):
        return export_rbi_daily_report_excel(queryset)
    

    @admin.action(description="Download Management Summary (PDF)")
    def download_management_summary(modeladmin, request, queryset):
        return export_management_summary_pdf()




# ===============================================================================
    

@admin.register(AMLAlert)
class AMLAlertAdmin(admin.ModelAdmin):

    list_display = (
        'account',
        'alert_type',
        'inr_amount',
        'is_resolved',
        'resolved_by',     # 🆕
        'resolved_at', 
        'created_at',
    )

    

    list_filter = (
        'alert_type',
        'is_resolved',
    )

    search_fields = ('account__account_number',)

    actions = ['resolve_selected_alerts', 'download_aml_alerts', 'download_aml_alerts_pdf', 'download_aml_alerts_excel']

    readonly_fields = (
        'account',
        'alert_type',
        'description',
        'inr_amount',
        'created_at',
    )

    def resolve_selected_alerts(self, request, queryset):
        updated = queryset.update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=now(),
            resolution_note="Reviewed and cleared by compliance"
        )

        self.message_user(
            request,
            f"{updated} AML alert(s) resolved successfully."
        )

    resolve_selected_alerts.short_description = "Resolve selected AML alerts"


    @admin.action(description="Download AML Alerts (CSV)")
    def download_aml_alerts(modeladmin, request, queryset):
        return export_aml_alerts_csv(queryset)
    

    @admin.action(description="Download AML Alerts (PDF)")
    def download_aml_alerts_pdf(modeladmin, request, queryset):
        return export_aml_alerts_pdf(queryset)
    
    @admin.action(description="Download AML Report (Excel)")
    def download_aml_alerts_excel(modeladmin, request, queryset):
        return export_aml_alerts_excel(queryset)

    
# ===============================================================================


@admin.register(TransactionFee)
class TransactionFeeAdmin(admin.ModelAdmin):

    list_display = (
        'transaction',
        'fee_amount',
        'currency',
        'inr_equivalent',
        'reason',
        'created_at',
    )

    list_filter = ('reason', 'currency', 'created_at')
    search_fields = ('transaction__id',)

    readonly_fields = (
        'transaction',
        'fee_amount',
        'currency',
        'inr_equivalent',
        'reason',
        'created_at',
    )

    actions = ['download_fx_income', 'download_fx_income_pdf', 'download_fx_income_excel']

    @admin.action(description="Download FX Income Report (CSV)")
    def download_fx_income(modelAdmin, request, queryset):
        return export_fx_income_csv(queryset)
    

    @admin.action(description="Download FX Income Report (PDF)")
    def download_fx_income_pdf(modeladmin, request, queryset):
        return export_fx_income_pdf(queryset)
    

    @admin.action(description="Download FX Income Report (Excel)")
    def download_fx_income_excel(modeladmin, request, queryset):
        return export_fx_income_excel(queryset)

# ===============================================================================



@admin.register(GSTLedger)
class GSTLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_fee_id",
        "fx_fee_amount",
        "gst_rate",
        "gst_amount",
        "inr_equivalent",
        "created_at",
    )

    readonly_fields = (
        "transaction_fee",
        "gst_rate",
        "gst_amount",
        "inr_equivalent",
        "created_at",
    )

    list_filter = ("gst_rate", "created_at",)

    actions = ["download_gst_report", "download_gst_excel", "download_gst_pdf", "download_monthly_gst_excel", "download_monthly_gst_pdf", "download_monthly_gst_csv", "download_fx_gst_compliance",]

    @admin.action(description="Download GST Report (CSV)")
    def download_gst_report(self, request, queryset):
        return export_gst_report_csv(queryset)
    
    @admin.action(description="Download GST Report (Excel)")
    def download_gst_excel(self, request, queryset):
        return export_gst_report_excel(queryset)
    
    @admin.action(description="Download GST Report (PDF)")
    def download_gst_pdf(self, request, queryset):
        return export_gst_report_pdf(queryset)
    

    @admin.action(description="Download Monthly GST Summary (CSV)")
    def download_monthly_gst_csv(self, request, queryset):
        return export_monthly_gst_csv()
    

    @admin.action(description="Download Monthly GST Summary (Excel)")
    def download_monthly_gst_excel(self, request, queryset):
        return export_monthly_gst_excel()

    @admin.action(description="Download Monthly GST Summary (PDF)")
    def download_monthly_gst_pdf(self, request, queryset):
        return export_monthly_gst_pdf()

    # ---------------------------------------------------------
    # FX + GST COMPLIANCE — CSV
    # ---------------------------------------------------------
    @admin.action(description="Download FX + GST Compliance (CSV)")
    def download_fx_gst_compliance_csv(self, request, queryset):
        start_date = date.today().replace(day=1)
        end_date = date.today()
        return export_fx_gst_compliance_csv(start_date, end_date)

    # ---------------------------------------------------------
    # FX + GST COMPLIANCE — EXCEL
    # ---------------------------------------------------------
    @admin.action(description="Download FX + GST Compliance (Excel)")
    def download_fx_gst_compliance_excel(self, request, queryset):
        start_date = date.today().replace(day=1)
        end_date = date.today()
        return export_fx_gst_compliance_excel(start_date, end_date)

    # ---------------------------------------------------------
    # FX + GST COMPLIANCE — PDF
    # ---------------------------------------------------------
    @admin.action(description="Download FX + GST Compliance (PDF)")
    def download_fx_gst_compliance_pdf(self, request, queryset):
        start_date = date.today().replace(day=1)
        end_date = date.today()
        return export_fx_gst_compliance_pdf(start_date, end_date)
    


    def transaction_fee_id(self, obj):
        return obj.transaction_fee.id
    transaction_fee_id.short_description = "Transaction Fee ID"

    def fx_fee_amount(self, obj):
        return obj.transaction_fee.inr_equivalent
    fx_fee_amount.short_description = "FX Fee Amount (INR)"

