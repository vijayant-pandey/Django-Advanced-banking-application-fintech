from decimal import Decimal
from datetime import time, timedelta

from django.utils.timezone import localtime, now

from transactions.services import settle_transfer
from transactions.services_fx import settle_fx_transfer, create_fx_rate_lock
from transactions.models import TransactionFee, Transaction
from decimal import Decimal
import math
import threading
import json
import hmac
import hashlib
import json
from django.conf import settings
import requests


# -------------------RULES-----------------------------------
# ================= NEFT WINDOW (RBI STYLE) =================

NEFT_START_TIME = time(9, 0)    # 09:00 AM
NEFT_END_TIME   = time(19, 0)   # 07:00 PM


# ================= RTGS RULES =================

RTGS_MIN_AMOUNT = Decimal("200000.00")  # ₹2,00,000
RTGS_FLAT_FEE   = Decimal("25.00")      # ₹25 flat

from decimal import Decimal


# ------------------------------------------------------------------
# ------------------------MAIN LOGIC--------------------------------
# ------------------------------------------------------------------

# FOR NEFT
def is_neft_window_open():
    """
    Returns True if current IST time is within NEFT window.
    """
    current_time = localtime(now()).time()
    return NEFT_START_TIME <= current_time <= NEFT_END_TIME


# ------------------------------------------------------------------

# FOR RTGS
def validate_rtgs(transfer):
    """
    Enforce RTGS minimum amount.
    """
    if transfer.amount < RTGS_MIN_AMOUNT:
        raise ValueError(
            f"RTGS minimum amount is ₹{RTGS_MIN_AMOUNT}"
        )


def create_rtgs_fee(reference_number):
    """
    Create flat RTGS service fee (linked to debit txn).
    """
    debit_txn = (
        Transaction.objects
        .filter(
            reference_number=reference_number,
            transaction_type='WITHDRAW'
        )
        .order_by('-id')
        .first()
    )

    if not debit_txn:
        return

    TransactionFee.objects.create(
        transaction=debit_txn,
        fee_amount=RTGS_FLAT_FEE,
        currency=debit_txn.currency,
        inr_equivalent=RTGS_FLAT_FEE,
        reason="RTGS Service Fee"
    )


# ------------------------------------------------------------------

# FOR IMPS
def calculate_imps_fee(amount: Decimal) -> Decimal:
    """
    IMPS slab-based service fee (INR).
    Charged to sender.
    """

    amount = Decimal(amount)

    if amount <= 1000:
        return Decimal("2.50")

    if amount <= 10000:
        return Decimal("5.00")

    if amount <= 100000:
        return Decimal("10.00")

    # Above 1,00,000
    extra_blocks = math.ceil((amount - 100000) / 100000)
    return Decimal("10.00") + Decimal(extra_blocks * 5)


#  -------------------------------------------------------------------
# FOR UPI
UPI_INTENT_TTL_MINUTES = 3  # RBI-style (can be 5–10)

def create_upi_intent(transfer):
    transfer.status = 'PENDING'
    transfer.upi_intent_status = 'CREATED'
    transfer.upi_intent_created_at = now()
    transfer.upi_intent_expires_at = now() + timedelta(minutes=UPI_INTENT_TTL_MINUTES)
    transfer.save(update_fields=[
        'status',
        'upi_intent_status',
        'upi_intent_created_at',
        'upi_intent_expires_at'
    ])


# ------------------------------------------------------------------

def dispatch_settlement(transfer, performed_by=None):
    """
    Central payment lifecycle dispatcher.
    """

    # 🛑 DOUBLE-SETTLEMENT GUARD
    if transfer.status in ['SETTLED', 'REVERSED']:
        return


    # ================= INTERNAL =================
    if transfer.channel == 'INTERNAL':
        settle_transfer(transfer, performed_by)
        return


    # ================= RTGS =================
    if transfer.channel == 'RTGS':
        # 1️⃣ Enforce and Validate RTGS rules
        validate_rtgs(transfer)

        # 2️⃣ Lifecycle move
        if transfer.status == 'INITIATED':
            transfer.status = 'PENDING'
            transfer.save(update_fields=['status'])

        # 3️⃣ Immediate settlement
        settle_transfer(transfer, performed_by)

        # 4️⃣ Flat RTGS service fee
        create_rtgs_fee(transfer.reference_number)
        return


    # ================= IMPS =================

    if transfer.channel == 'IMPS':
    # 1️⃣ Settle money first
        settle_transfer(transfer, performed_by)

        # 2️⃣ Apply IMPS service fee (sender pays)
        fee_amount = calculate_imps_fee(Decimal(transfer.amount))


        sender_txn = (
            Transaction.objects
            .filter(
                transaction_type='WITHDRAW',
                reference_number=transfer.reference_number
            )
            .order_by('-id')
            .first()
        )

        if sender_txn:
            TransactionFee.objects.create(
                transaction=sender_txn,
                fee_amount=fee_amount,
                currency=sender_txn.currency,
                inr_equivalent=fee_amount,
                reason="IMPS Service Fee"
            )

        return


    # ================= FX =================
    if transfer.channel == 'FX':
        if transfer.status == 'APPROVED':
            settle_fx_transfer(transfer, performed_by)
        return
    

    # ================= NEFT =================
    if transfer.channel == 'NEFT':
        # 🚫 NEVER SETTLE HERE
        if transfer.status == 'INITIATED':
            transfer.status = 'PENDING'
            transfer.save(update_fields=['status'])
        return


    # ================= UPI =================

    if transfer.channel == 'UPI':

        # 🚫 HARD GUARD
        if transfer.status in ['SETTLED', 'EXPIRED', 'REVERSED']:
            return

        # Create intent
        if transfer.status == 'INITIATED':
            create_upi_intent(transfer)

        # Approved → settle
        if transfer.status == 'APPROVED':
            settle_transfer(transfer, performed_by)
            return

