from decimal import Decimal
from django.db import transaction
from transactions.models import Transaction
from django.utils.timezone import now


@transaction.atomic
def credit_savings_interest(account):
    monthly_rate = account.interest_rate / Decimal('100') / Decimal('12')
    interest_amount = account.balance * monthly_rate

    if interest_amount <= 0:
        return

    new_balance = account.balance + interest_amount

    Transaction.objects.create(
        account=account,
        transaction_type='DEPOSIT',
        amount=interest_amount,
        balance_after_transaction=new_balance
    )

    account.balance = new_balance
    account.save()




from django.utils.timezone import now

@transaction.atomic
def mature_fd(fd):
    if fd.is_matured:
        return

    total_interest = (
        fd.principal *
        (fd.interest_rate / Decimal('100')) *
        (fd.tenure_months / Decimal('12'))
    )

    maturity_amount = fd.principal + total_interest
    account = fd.account

    new_balance = account.balance + maturity_amount

    Transaction.objects.create(
        account=account,
        transaction_type='DEPOSIT',
        amount=maturity_amount,
        balance_after_transaction=new_balance
    )

    account.balance = new_balance
    account.save()

    fd.is_matured = True
    fd.save()
