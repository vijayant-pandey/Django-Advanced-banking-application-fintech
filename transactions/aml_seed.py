from decimal import Decimal
from django.utils.timezone import now, timedelta

from accounts.models import BankAccount, Currency
from transactions.models import Transaction
from transactions.aml import (
    check_daily_limit,
    check_rapid_transactions,
    check_suspicious_fx
)


def seed_aml_test_data():
    """
    ⚠️ FOR TESTING ONLY
    Creates transactions that intentionally trigger AML alerts
    """

    acc = BankAccount.objects.first()
    if not acc:
        print("❌ No bank account found")
        return

    inr = Currency.objects.get(code='INR')
    usd = Currency.objects.get(code='USD')

    print(f"🔎 Seeding AML data for account: {acc.account_number}")

    # --------------------------------------------------
    # 1️⃣ DAILY LIMIT BREACH (₹12,00,000)
    # --------------------------------------------------
    Transaction.objects.create(
        account=acc,
        wallet=acc.wallets.get(currency=inr),
        transaction_type='DEPOSIT',
        amount=Decimal('1200000.00'),
        currency=inr,
        inr_equivalent=Decimal('1200000.00'),
        balance_after_transaction=Decimal('1200000.00'),
        created_at=now()
    )

    check_daily_limit(acc)

    # --------------------------------------------------
    # 2️⃣ RAPID TRANSACTIONS (6 tx in 10 min)
    # --------------------------------------------------
    for i in range(6):
        Transaction.objects.create(
            account=acc,
            wallet=acc.wallets.get(currency=inr),
            transaction_type='WITHDRAW',
            amount=Decimal('1000.00'),
            currency=inr,
            inr_equivalent=Decimal('1000.00'),
            balance_after_transaction=Decimal('1000000.00'),
            created_at=now() - timedelta(minutes=5)
        )

    check_rapid_transactions(acc)

    # --------------------------------------------------
    # 3️⃣ SUSPICIOUS FX ACTIVITY (₹6,00,000 FX)
    # --------------------------------------------------
    Transaction.objects.create(
        account=acc,
        wallet=acc.wallets.get(currency=usd),
        transaction_type='WITHDRAW',
        amount=Decimal('7000.00'),  # USD
        currency=usd,
        inr_equivalent=Decimal('600000.00'),
        balance_after_transaction=Decimal('1000.00'),
        created_at=now()
    )

    check_suspicious_fx(acc)

    print("✅ AML test data seeded")
