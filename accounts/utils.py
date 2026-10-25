import random
from .models import Wallet, Currency


def generate_account_number():
    return '1001' + ''.join([str(random.randint(0, 9)) for _ in range(10)])


def get_or_create_wallet(bank_account, currency_code):
    currency = Currency.objects.get(code=currency_code)

    wallet, created = Wallet.objects.get_or_create(
        bank_account=bank_account,
        currency=currency,
        defaults={'balance': 0}
    )

    return wallet
