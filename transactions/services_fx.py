from decimal import Decimal
from django.db import transaction as db_transaction
from transactions.models import Transaction, TransactionFee, GSTLedger
from audit.utils import log_action
# from accounts.utils import get_or_create_wallet
from accounts.wallet_services import get_or_create_wallet
from accounts.fx_engine import FXEngine
from transactions.aml import (
    check_daily_limit,
    check_rapid_transactions,
    check_suspicious_fx
)

import uuid
from datetime import datetime
from django.utils.timezone import now
from datetime import timedelta
from transactions.models import FXRateLock

from accounts.fx_engine import FXEngine 
from accounts.models import Currency



FX_LOCK_TTL_MINUTES = 3


def create_fx_rate_lock(transfer):
    """
    Locks FX rate at approval time.
    """

    if hasattr(transfer, 'fx_rate_lock'):
        return transfer.fx_rate_lock

    rate = FXEngine.get_rate(
        transfer.currency.code,
        'INR'
    )

    lock = FXRateLock.objects.create(
        transfer=transfer,
        from_currency=transfer.currency,
        to_currency=Currency.objects.get(code='INR'),
        rate=Decimal(rate),
        expires_at=now() + timedelta(minutes=FX_LOCK_TTL_MINUTES)
    )

    return lock



# @db_transaction.atomic
# def settle_fx_transfer(transfer, performed_by=None):
#     """
#     FX settlement with conversion, spread, GST.
#     """

#     if transfer.status != 'PENDING':
#         return

#     amount = Decimal(transfer.amount)
    # source_currency = transfer.currency.code
    # base_currency = FXEngine.BASE_CURRENCY  # INR

    # from_wallet = get_or_create_wallet(
    #     transfer.from_account,
    #     source_currency
    # )
    # to_wallet = get_or_create_wallet(
    #     transfer.to_account,
    #     base_currency
    # )

    # if from_wallet.balance < amount:
    #     transfer.status = 'FAILED'
    #     transfer.save()
    #     return

    # # FX conversion
    # fx = FXEngine.convert_with_details(
    #     amount,
    #     source_currency,
    #     base_currency
    # )

    # inr_value = fx['converted_amount']
    # spread_amount = fx['spread_amount']

    # # Move balances
    # from_wallet.balance -= amount
    # to_wallet.balance += inr_value

    # debit_txn = Transaction.objects.create(
    #     account=transfer.from_account,
    #     wallet=from_wallet,
    #     transaction_type='WITHDRAW',
    #     amount=amount,
    #     currency=transfer.currency,
    #     inr_equivalent=inr_value,
    #     balance_after_transaction=from_wallet.balance,
    #     mode='ELECTRONIC',
    #     channel='FX',
    #     reference_number=transfer.reference_number,
    # )

    # credit_txn = Transaction.objects.create(
    #     account=transfer.to_account,
    #     wallet=to_wallet,
    #     transaction_type='DEPOSIT',
    #     amount=inr_value,
    #     currency=to_wallet.currency,
    #     inr_equivalent=inr_value,
    #     balance_after_transaction=to_wallet.balance,
    #     mode='ELECTRONIC',
    #     channel='FX',
    #     reference_number=transfer.reference_number,
    # )

    # # FX Fee
    # fee = TransactionFee.objects.create(
    #     transaction=credit_txn,
    #     fee_amount=spread_amount,
    #     currency=to_wallet.currency,
    #     inr_equivalent=spread_amount,
    #     reason="FX Spread"
    # )

    # # GST
    # gst_amount = (spread_amount * Decimal("0.18")).quantize(Decimal("0.01"))

    # GSTLedger.objects.create(
    #     transaction_fee=fee,
    #     gst_rate=18,
    #     gst_amount=gst_amount,
    #     inr_equivalent=gst_amount
    # )

    # from_wallet.save()
    # to_wallet.save()

    # transfer.status = 'SETTLED'
    # transfer.settled_at = now()
    # transfer.save()




# ============================================================
# FX SETTLEMENT
# ============================================================

@db_transaction.atomic
def settle_fx_transfer(transfer, performed_by=None):
    """
    FX settlement with locked rate, spread & GST.
    """

    # 🔒 Guard
    if transfer.status not in ['PENDING', 'APPROVED']:
        return

    fx_lock = transfer.fx_rate_lock

    # ⏰ Expired rate lock
    if now() > fx_lock.expires_at:
        fx_lock.is_expired = True
        fx_lock.save(update_fields=['is_expired'])

        transfer.status = 'FAILED'
        transfer.save(update_fields=['status'])
        return

    amount = Decimal(transfer.amount)
    source_currency = transfer.currency.code
    base_currency = FXEngine.BASE_CURRENCY  # INR

    from_wallet = get_or_create_wallet(
        transfer.from_account,
        source_currency
    )
    to_wallet = get_or_create_wallet(
        transfer.to_account,
        base_currency
    )

    if from_wallet.balance < amount:
        transfer.status = 'FAILED'
        transfer.save(update_fields=['status'])
        return

    # FX conversion using LOCKED rate
    base_rate = fx_lock.rate
    final_rate = FXEngine.apply_spread(base_rate)

    inr_value = (amount * final_rate).quantize(Decimal("0.01"))
    spread_amount = ((final_rate - base_rate) * amount).quantize(Decimal("0.01"))

    # Move balances
    from_wallet.balance -= amount
    to_wallet.balance += inr_value

    from_wallet.save()
    to_wallet.save()

    # Debit (Foreign Currency)
    debit_txn = Transaction.objects.create(
        account=transfer.from_account,
        wallet=from_wallet,
        transaction_type='WITHDRAW',
        amount=amount,
        currency=transfer.currency,
        inr_equivalent=inr_value,
        balance_after_transaction=from_wallet.balance,
        mode='ELECTRONIC',
        channel='FX',
        reference_number=transfer.reference_number,
    )

    # Credit (INR)
    credit_txn = Transaction.objects.create(
        account=transfer.to_account,
        wallet=to_wallet,
        transaction_type='DEPOSIT',
        amount=inr_value,
        currency=to_wallet.currency,
        inr_equivalent=inr_value,
        balance_after_transaction=to_wallet.balance,
        mode='ELECTRONIC',
        channel='FX',
        reference_number=transfer.reference_number,
    )

    # FX Spread Fee
    fee = TransactionFee.objects.create(
        transaction=credit_txn,
        fee_amount=spread_amount,
        currency=to_wallet.currency,
        inr_equivalent=spread_amount,
        reason="FX Spread"
    )

    # GST @ 18%
    gst_amount = (spread_amount * Decimal("0.18")).quantize(Decimal("0.01"))

    GSTLedger.objects.create(
        transaction_fee=fee,
        gst_rate=18,
        gst_amount=gst_amount,
        inr_equivalent=gst_amount
    )

    transfer.status = 'SETTLED'
    transfer.settled_at = now()
    transfer.save(update_fields=['status', 'settled_at'])

    log_action(
        user=performed_by,
        action_type='TRANSFER_SETTLED',
        description=f"FX transfer settled | Ref {transfer.reference_number}"
    )
