from accounts.models import Wallet, Currency
from decimal import Decimal


def get_or_create_wallet(account, currency_code):
    currency = Currency.objects.get(code=currency_code)

    wallet, _ = Wallet.objects.get_or_create(
        bank_account=account,
        currency=currency,
        defaults={'balance': Decimal('0.00')}
    )
    return wallet




