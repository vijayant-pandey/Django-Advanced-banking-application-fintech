from django.db import models
from accounts.models import BankAccount
from accounts.models import Wallet, Currency


class Transaction(models.Model):

    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAW', 'Withdraw'),
    )
    
    MODE_CHOICES = (
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        # ('ONLINE', 'Online'),
        ('ELECTRONIC', 'Electronic'),
        
    )

    CHANNEL_CHOICES = (
        ('NEFT', 'NEFT'),
        ('RTGS', 'RTGS'),
        ('IMPS', 'IMPS'),
        ('UPI', 'UPI'),
        ('INTERNAL', 'Internal Transfer'),
        ('FX', 'FX Transfer'),
    )

    
    
    # 🔒 Legacy compatibility (will be removed later)
    account = models.ForeignKey(
        BankAccount, 
        on_delete=models.CASCADE
    )
    
    # ✅ REAL SOURCE OF TRUTH
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True,
        blank=True
    )

    transaction_type = models.CharField(
        max_length=10, 
        choices=TRANSACTION_TYPES
    )
    
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2
    )

    inr_equivalent = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="INR equivalent at transaction time"
    )

    balance_after_transaction = models.DecimalField(
        max_digits=12, 
        decimal_places=2
    )
    
    # wallet = models.ForeignKey(
    #     Wallet,
    #     on_delete=models.CASCADE,
    #     null=True,
    #     blank=True
    # )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    # 🆕 NEW FIELDS (ADD HERE)
    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        # default='ONLINE'
        default='ELECTRONIC'

    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        null=True,
        blank=True
    )

    reference_number = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )


    cheque_number = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # def __str__(self):
    #     # return f"{self.transaction_type} - {self.amount} "
    #     return f"{self.transaction_type} {self.amount} {self.wallet.currency.code}"


    def __str__(self):
        currency = (
            self.wallet.currency.code
            if self.wallet and self.wallet.currency
            else (self.currency.code if self.currency else 'N/A')
        )
        return f"{self.transaction_type} {self.amount} {currency}"

# ---------------------------------------------------------------------------------------

class TransferRequest(models.Model):

    STATUS_CHOICES = (
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('SETTLED', 'Settled'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
        ('EXPIRED', 'Expired'),   # 🆕
    )


    from_account = models.ForeignKey(
        BankAccount,
        related_name='outgoing_transfers',
        on_delete=models.CASCADE
    )

    to_account = models.ForeignKey(
        BankAccount,
        related_name='incoming_transfers',
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        # null=True,
        # blank=True
    )

    channel = models.CharField(
        max_length=20,
        # choices=Transaction.CHANNEL_CHOICES,
        choices=(
            ('NEFT', 'NEFT'),
            ('RTGS', 'RTGS'),
            ('IMPS', 'IMPS'),
            ('UPI', 'UPI'),
            ('INTERNAL', 'Internal'),
            ('FX', 'FX'),
        ),
        default='INTERNAL'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='INITIATED'
    )

    reference_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True
    )

    # 🆕 ADD THIS (NEFT BATCH ID)
    neft_batch_id = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    settled_at = models.DateTimeField(
        null=True,
        blank=True
    )


    # ================== UPI INTENT FIELDS ==================
    upi_intent_created_at = models.DateTimeField(
        null=True,
        blank=True
    )

    upi_intent_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    upi_intent_status = models.CharField(
        max_length=20,
        choices=(
            ('CREATED', 'Created'),
            ('APPROVED', 'Approved'),
            ('EXPIRED', 'Expired'),
            ('REJECTED', 'Rejected'),
        ),
        null=True,
        blank=True
    )

    is_merchant_payment = models.BooleanField(default=False)


    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_account} → {self.to_account}"

# ---------------------------------------------------------------------------------------


class FXRateLock(models.Model):
    transfer = models.OneToOneField(
        'TransferRequest',
        on_delete=models.CASCADE,
        related_name='fx_rate_lock'
    )

    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='+'
    )

    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='+'
    )

    rate = models.DecimalField(
        max_digits=12,
        decimal_places=6
    )

    locked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    is_expired = models.BooleanField(default=False)

    def __str__(self):
        return f"FX Lock {self.rate} ({self.from_currency.code}→{self.to_currency.code})"




# ---------------------------------------------------------------------------------------


class TransactionFee(models.Model):
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='fee'
    )
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    inr_equivalent = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=100)  # FX fee, Transfer fee, GST
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fee {self.fee_amount} {self.currency.code}"
    

class AMLAlert(models.Model):

    ALERT_TYPES = (
        ('DAILY_LIMIT', 'Daily Limit Exceeded'),
        ('RAPID_TX', 'Rapid Transactions'),
        ('SUSPICIOUS_FX', 'Suspicious FX Activity'),
    )

    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='aml_alerts'
    )

    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES
    )

    

    description = models.TextField()

    inr_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    is_resolved = models.BooleanField(default=False)


    # 🆕 ADD THESE
    resolved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    resolution_note = models.TextField(
        blank=True,
        null=True
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account.account_number} - {self.alert_type}"



class GSTLedger(models.Model):
    transaction_fee = models.OneToOneField(
        TransactionFee,
        on_delete=models.CASCADE,
        related_name="gst"
    )

    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00
    )

    gst_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    inr_equivalent = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GST ₹{self.gst_amount} on Fee {self.transaction_fee.id}"
