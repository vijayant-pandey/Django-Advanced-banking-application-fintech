from django.db import models
from customers.models import Customer
from decimal import Decimal


class BankAccount(models.Model):

    ACCOUNT_TYPES = (
        ('SAVINGS', 'Savings Account'),
        ('CURRENT', 'Current Account'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, unique=True)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="DEPRECATED: use Wallet.balance instead")

    is_active = models.BooleanField(default=False)   # admin approval
    is_frozen = models.BooleanField(default=False)  # NEW
    created_at = models.DateTimeField(auto_now_add=True)


    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.50')  # Savings default
    )

    def __str__(self):
        return self.account_number



class FixedDeposit(models.Model):
    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE
    )
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.IntegerField()
    start_date = models.DateField(auto_now_add=True)
    maturity_date = models.DateField()
    is_matured = models.BooleanField(default=False)

    def __str__(self):
        return f"FD - {self.account.account_number}"
    

class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)  # INR, USD, EUR
    name = models.CharField(max_length=50)              # Indian Rupee
    symbol = models.CharField(max_length=5)             # ₹, $, €
    decimal_places = models.IntegerField(default=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class Wallet(models.Model):
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='wallets'
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT
    )
    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        # default=0.00,
        default=Decimal('0.00')
    )

    class Meta:
        unique_together = ('bank_account', 'currency')

    def __str__(self):
        return f"{self.bank_account.account_number} - {self.currency.code}"



class FXRate(models.Model):
    base_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='base_rates'
    )
    target_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='target_rates'
    )
    rate = models.DecimalField(max_digits=12, decimal_places=6)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('base_currency', 'target_currency')

    def __str__(self):
        return f"{self.base_currency.code} → {self.target_currency.code}"
