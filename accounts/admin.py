from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import BankAccount
from .models import Currency
from .models import Wallet


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        'account_number',
        'customer',
        'account_type',
        'balance',
        'is_active',
        'is_frozen',
    )
    list_filter = ('account_type', 'is_active', 'is_frozen')
    search_fields = ('account_number', 'is_active', 'is_frozen')
    readonly_fields = ('balance',)




@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'is_active')
    list_filter = ('is_active',)



@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('bank_account', 'currency', 'balance')
    list_filter = ('currency',)


from .models import FXRate

@admin.register(FXRate)
class FXRateAdmin(admin.ModelAdmin):
    list_display = (
        'base_currency',
        'target_currency',
        'rate',
        'fetched_at',
    )
    list_filter = ('base_currency',)
