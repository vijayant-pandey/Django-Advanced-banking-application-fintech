from decimal import Decimal
from django.db import transaction as db_transaction
from .models import Transaction, TransactionFee, GSTLedger
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


# ==========================================================================================


@db_transaction.atomic
def deposit(account, amount, performed_by=None):
    amount = Decimal(amount)

    new_balance = account.balance + amount

    Transaction.objects.create(
        account=account,
        transaction_type='DEPOSIT',
        amount=amount,
        balance_after_transaction=new_balance
    )

    account.balance = new_balance
    account.save()

    log_action(
        user=performed_by,
        action_type='CREATE',
        description=f'Deposit of {amount} into {account.account_number}'
    )
# ==========================================================================================

@db_transaction.atomic
def deposit_to_wallet(account, amount, currency_code, performed_by):
    amount = Decimal(amount)

    wallet = get_or_create_wallet(account, currency_code)

    new_balance = wallet.balance + amount

    Transaction.objects.create(
        account=account,              # ✅ ADD THIS
        wallet=wallet,
        transaction_type='DEPOSIT',
        amount=amount,
        balance_after_transaction=new_balance,
        currency=wallet.currency,
        inr_equivalent=FXEngine.convert(amount, wallet.currency.code, 'INR')
    )

    wallet.balance = new_balance
    wallet.save()

    log_action(
        user=performed_by,
        action_type='CREATE',
        description=(
            f"Deposit {amount} {currency_code} "
            f"into wallet {wallet.id}"
        )
    )
# ==========================================================================================


@db_transaction.atomic
def withdraw(account, amount, performed_by=None):
    amount = Decimal(amount)

    if account.balance < amount:
        raise ValueError("Insufficient balance")

    new_balance = account.balance - amount

    Transaction.objects.create(
        account=account,
        transaction_type='WITHDRAW',
        amount=amount,
        balance_after_transaction=new_balance
    )

    account.balance = new_balance
    account.save()

    log_action(
        user=performed_by,
        action_type='DELETE',
        description=f'Withdraw of {amount} from {account.account_number}'
    )
# ==========================================================================================


@db_transaction.atomic
def withdraw_from_wallet(account, amount, currency_code, performed_by):
    amount = Decimal(amount)

    wallet = get_or_create_wallet(account, currency_code)

    if wallet.balance < amount:
        raise ValueError("Insufficient funds in selected currency")

    new_balance = wallet.balance - amount

    Transaction.objects.create(
        account=account,              # ✅ ADD THIS
        wallet=wallet,
        transaction_type='WITHDRAW',
        amount=amount,
        balance_after_transaction=new_balance,
        currency=wallet.currency,
        inr_equivalent=FXEngine.convert(amount, wallet.currency.code, 'INR')
    )

    wallet.balance = new_balance
    wallet.save()

    log_action(
        user=performed_by,
        action_type='DELETE',
        description=(
            f"Withdraw {amount} {currency_code} "
            f"from wallet {wallet.id}"
        )
    )


# ==========================================================================================

def _approve_transfer_only(transfer, performed_by):
    """
    Phase 13B.1 — Approval only (NO MONEY MOVEMENT)
    """
    # Idempotency guard
    if transfer.is_approved:
        return
    
    transfer.is_approved = True
    transfer.status = 'PENDING'

    if not transfer.reference_number:
        transfer.reference_number = (
            f"{transfer.channel}-{uuid.uuid4().hex[:12].upper()}"
        )

    transfer.save()

    log_action(
        user=performed_by,
        action_type='TRANSFER_APPROVED',
        description=(
            f"Transfer approved | "
            f"{transfer.channel} | "
            f"Ref {transfer.reference_number}"
        )
    )
# ==========================================================================================

@db_transaction.atomic
def approve_transfer(transfer, performed_by=None):
    """
    Approves a transfer request.
    Supports:
    - Same-currency transfers
    - Cross-currency FX transfers (with spread & fee)
    - FX Spread Fees
    - GST on FX Fees
    - Immutable + Idempotent ledger entries
    - INR normalization for audit & RBI reports
    """

    # ================================
    # PHASE 13B GUARD (DO NOT DELETE)
    # ================================

    # If lifecycle engine is enabled,
    # approval should NOT move money
    if hasattr(transfer, "status"):
        # Approval-only path (Phase 13B)
        return _approve_transfer_only(transfer, performed_by)

    # ------------------------------------------------------------------
    # BASIC DATA
    # ------------------------------------------------------------------
    # ------------------------------------------------------------
    # ⛔ IDPOTENCY GUARD (CRITICAL)
    # ------------------------------------------------------------
    if transfer.is_approved:
        return
    from_account = transfer.from_account
    to_account = transfer.to_account
    amount = Decimal(transfer.amount)
    source_currency = transfer.currency          # e.g. USD, EUR
    base_currency = FXEngine.BASE_CURRENCY        # INR

    # ------------------------------------------------------------------
    # SAFETY CHECKS
    # ------------------------------------------------------------------
    if from_account.is_frozen or to_account.is_frozen:
        raise ValueError("Account is frozen")

    # ------------------------------------------------------------------
    # SOURCE WALLET (ALWAYS IN SOURCE CURRENCY)
    # ------------------------------------------------------------------
    from_wallet = get_or_create_wallet(
        from_account,
        source_currency.code
    )

    if from_wallet.balance < amount:
        raise ValueError("Insufficient funds in selected currency")

    # ==================================================================
    # CASE 1: SAME-CURRENCY TRANSFER (e.g. INR → INR)
    # ==================================================================
    if source_currency.code == base_currency:

        to_wallet = get_or_create_wallet(
            to_account,
            source_currency.code,
            base_currency
        )

        # Move money
        from_wallet.balance -= amount
        to_wallet.balance += amount

        # Ledger — Debit
        Transaction.objects.create(
            account=from_account,
            wallet=from_wallet,
            transaction_type='WITHDRAW',
            amount=amount,
            balance_after_transaction=from_wallet.balance,
            currency=source_currency,
            inr_equivalent=amount,

            # 🆕 BANK-GRADE FIELDS
            mode='ELECTRONIC',
            channel=transfer.channel,
            reference_number=f"{transfer.channel}-{uuid.uuid4().hex[:10]}"
        )


        # Ledger — Credit
        Transaction.objects.create(
            account=to_account,
            wallet=to_wallet,
            transaction_type='DEPOSIT',
            amount=amount,
            balance_after_transaction=to_wallet.balance,
            currency=source_currency,
            inr_equivalent=amount,

            # 🆕 BANK-GRADE FIELDS
            mode='ELECTRONIC',
            channel=transfer.channel,
            reference_number=f"{transfer.channel}-{uuid.uuid4().hex[:10]}"
        )


        from_wallet.save()
        to_wallet.save()

        # Audit log (NO FX text)
        log_action(
            user=performed_by,
            action_type='TRANSFER',
            description=(
                f'Transfer approved: '
                f'{from_account.account_number} → '
                f'{to_account.account_number} | '
                f'{amount} {source_currency.code}'
            )
        )

    # ==================================================================
    # CASE 2: CROSS-CURRENCY TRANSFER (USD/EUR → INR)
    # ==================================================================
    else:
        # --------------------------------------------------------------
        # FX CONVERSION WITH DETAILS (RATE + SPREAD)
        # --------------------------------------------------------------
        fx = FXEngine.convert_with_details(
            amount,
            source_currency.code,
            base_currency
        )

        inr_value = fx['converted_amount']
        spread_amount = fx['spread_amount']
        base_rate = fx['base_rate']
        final_rate = fx['final_rate']

        # Target wallet is ALWAYS INR
        to_wallet = get_or_create_wallet(
            to_account,
            base_currency
        )

        # Move money
        from_wallet.balance -= amount
        to_wallet.balance += inr_value

        # --------------------------------------------------------------
        # LEDGER — SOURCE (WITHDRAW)
        # --------------------------------------------------------------
        source_txn = Transaction.objects.create(
            account=from_account,
            wallet=from_wallet,
            transaction_type='WITHDRAW',
            amount=amount,
            balance_after_transaction=from_wallet.balance,
            currency=source_currency,
            inr_equivalent=inr_value,

            # 🆕 BANK-GRADE FIELDS
            mode = "ELECTRONIC",
            channel = "FX",
            reference_number=f"FX-{uuid.uuid4().hex[:10]}"

        )

        # --------------------------------------------------------------
        # LEDGER — TARGET (DEPOSIT)
        # --------------------------------------------------------------
        target_txn = Transaction.objects.create(
            account=to_account,
            wallet=to_wallet,
            transaction_type='DEPOSIT',
            amount=inr_value,
            balance_after_transaction=to_wallet.balance,
            currency=to_wallet.currency,
            inr_equivalent=inr_value,

            # 🆕 BANK-GRADE FIELDS
            mode = "ELECTRONIC",
            channel = "FX",
            reference_number=f"FX-{uuid.uuid4().hex[:10]}"
        )



        # --------------------------------------------------------
        # FX FEE (IDEMPOTENT)
        # --------------------------------------------------------
        fee, _ = TransactionFee.objects.get_or_create(
            transaction=target_txn,
            defaults={
                "fee_amount": spread_amount,
                "currency": to_wallet.currency,
                "inr_equivalent": spread_amount,
                "reason": "FX Spread",
            },
        )

        # --------------------------------------------------------
        # GST ON FX FEE (18%) — IDEMPOTENT
        # --------------------------------------------------------
        GST_RATE = Decimal("18.00")
        gst_amount = (fee.inr_equivalent * GST_RATE / 100).quantize(
            Decimal("0.01")
        )

        GSTLedger.objects.get_or_create(
            transaction_fee=fee,
            defaults={
                "gst_rate": GST_RATE,
                "gst_amount": gst_amount,
                "inr_equivalent": gst_amount,
            },
        )


        from_wallet.save()
        to_wallet.save()

        # --------------------------------------------------------------
        # AUDIT LOG (WITH INR EQUIVALENT + FEE)
        # --------------------------------------------------------------
        log_action(
            user=performed_by,
            action_type='TRANSFER',
            description=(
                f'FX Transfer approved: '
                f'{from_account.account_number} → '
                f'{to_account.account_number} | '
                f'{amount} {source_currency.code} '
                f'(≈ ₹{inr_value} INR | FX Fee ₹{spread_amount} | GST ₹{gst_amount})'
            )
        )

    # ------------------------------------------------------------------
    # FINALIZE TRANSFER
    # ------------------------------------------------------------------
    transfer.is_approved = True
    transfer.save()


    check_daily_limit(from_account)
    check_rapid_transactions(from_account)
    check_suspicious_fx(from_account)

# ----------------------------------------------------------------------------- 

@db_transaction.atomic
def reverse_transaction(transaction, performed_by=None):

    account = transaction.account
    amount = transaction.amount

    if transaction.transaction_type == 'DEPOSIT':
        new_balance = account.balance - amount
        reversal_type = 'WITHDRAW'
    else:
        new_balance = account.balance + amount
        reversal_type = 'DEPOSIT'

    Transaction.objects.create(
        account=account,
        transaction_type=reversal_type,
        amount=amount,
        balance_after_transaction=new_balance
    )

    account.balance = new_balance
    account.save()

    # ✅ AUDIT LOG
    log_action(
        user=performed_by,
        action_type='REVERSAL',
        description=f'Transaction reversed (Txn ID: {transaction.id})'
    )
# ==========================================================================================


def reject_transfer(transfer, performed_by, reason=""):
    transfer.is_rejected = True
    transfer.rejection_reason = reason
    transfer.save()

    log_action(
        user=performed_by,
        action_type='TRANSFER',
        description=(
            f"Transfer REJECTED: "
            f"{transfer.from_account.account_number} → "
            f"{transfer.to_account.account_number}, "
            f"Amount {transfer.amount}, Reason: {reason}"
        )
    )
# ==========================================================================================



@db_transaction.atomic
def transfer_same_currency(
    from_account,
    to_account,
    amount,
    currency_code,
    performed_by
):
    amount = Decimal(amount)

    from_wallet = get_or_create_wallet(from_account, currency_code)
    to_wallet = get_or_create_wallet(to_account, currency_code)

    if from_wallet.balance < amount:
        raise ValueError("Insufficient funds")

    from_wallet.balance -= amount
    to_wallet.balance += amount


    Transaction.objects.create(
        account=from_account,          # ✅ REQUIRED
        wallet=from_wallet,
        transaction_type='WITHDRAW',
        amount=amount,
        balance_after_transaction=from_wallet.balance
    )

    Transaction.objects.create(
        account=to_account,            # ✅ REQUIRED
        wallet=to_wallet,
        transaction_type='DEPOSIT',
        amount=amount,
        balance_after_transaction=to_wallet.balance
    )

    from_wallet.save()
    to_wallet.save()
# ==========================================================================================


@db_transaction.atomic
def settle_transfer(transfer, performed_by=None):
    """
    Executes money movement ONLY for approved & pending transfers.
    """

    if transfer.status not in ['PENDING', 'APPROVED']:
        return

    from_account = transfer.from_account
    to_account = transfer.to_account
    amount = Decimal(transfer.amount)
    currency = transfer.currency

    # ================= INR EQUIVALENT LOGIC =================
    # 🚫 NO FX conversion for domestic INR transfers
    if currency.code == 'INR':
        inr_equivalent = amount
    else:
        inr_equivalent = FXEngine.convert(amount, currency.code, 'INR')

    from_wallet = get_or_create_wallet(from_account, currency.code)
    to_wallet = get_or_create_wallet(to_account, currency.code)

    if from_wallet.balance < amount:
        transfer.status = 'FAILED'
        # transfer.save()
        transfer.save(update_fields=['status'])

        return

    # Move money
    from_wallet.balance -= amount
    to_wallet.balance += amount

    # Ledger - DEBIT entries
    Transaction.objects.create(
        account=from_account,
        wallet=from_wallet,
        transaction_type='WITHDRAW',
        amount=amount,
        currency=currency,
        inr_equivalent=inr_equivalent,
        balance_after_transaction=from_wallet.balance,
        mode='ELECTRONIC',
        channel=transfer.channel,                    # ✅ ADD
        reference_number=transfer.reference_number 
    )
    
    # Ledger CREDIT Entried
    Transaction.objects.create(
        account=to_account,
        wallet=to_wallet,
        transaction_type='DEPOSIT',
        amount=amount,
        currency=currency,
        inr_equivalent=inr_equivalent,
        balance_after_transaction=to_wallet.balance,
        mode='ELECTRONIC',
        channel=transfer.channel,                    # ✅ ADD
        reference_number=transfer.reference_number   # ✅ ADD
    )

    # from_wallet.save()
    # to_wallet.save()

    from_wallet.save(update_fields=['balance'])
    to_wallet.save(update_fields=['balance'])

    transfer.status = 'SETTLED'
    transfer.settled_at = now()
    transfer.save(update_fields=['status', 'settled_at'])

    log_action(
        user=performed_by,
        action_type='TRANSFER_SETTLED',
        description=f"Transfer settled | Ref {transfer.reference_number}"
    )


# =====================================================================================
