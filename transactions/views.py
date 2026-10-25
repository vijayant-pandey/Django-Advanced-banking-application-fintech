from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import BankAccount
from .services import deposit, withdraw
from .models import Transaction
from .models import TransferRequest
from audit.utils import log_action
from audit.helpers import get_client_ip
from .services import approve_transfer
from .services import reverse_transaction
from django.utils.timezone import now
from django.db.models import Sum
from .constants import DAILY_TRANSFER_LIMIT
from decimal import Decimal, InvalidOperation
from django.http import FileResponse
from .pdf import generate_statement_pdf
from .services import deposit_to_wallet
from accounts.models import Currency
from .services import withdraw_from_wallet
from transactions.services import deposit_to_wallet
from django.db.models import Q


#  ---------------------------------------------------------------------------------------


@login_required
def deposit_view(request):
    account = BankAccount.objects.get(customer__user=request.user)
    currencies = Currency.objects.filter(is_active=True)


    if request.method == 'POST':
        amount = request.POST.get('amount')
        currency_code = request.POST.get('currency')


        # deposit(
        #     account=account,
        #     amount=amount,
        #     performed_by=request.user   # ✅ PASS HERE
        # )

        deposit_to_wallet(
            account=account,
            amount=amount,
            currency_code=currency_code,
            performed_by=request.user
        )

        
        return redirect('dashboard')

    return render(request, 'transactions/deposit.html', {'currencies': currencies})

#  ---------------------------------------------------------------------------------------


@login_required
def withdraw_view(request):
    account = BankAccount.objects.get(customer__user=request.user)
    currencies = Currency.objects.filter(is_active=True)
    error = None

    if request.method == 'POST':
        amount = request.POST.get('amount')
        currency_code = request.POST.get('currency')
        try:
            # withdraw(
            #     account=account,
            #     amount=amount,
            #     performed_by=request.user   # ✅ PASS HERE
            # )
            withdraw_from_wallet(
                account=account,
                amount=amount,
                currency_code=currency_code,
                performed_by=request.user
            )
            return redirect('dashboard')
        except ValueError as e:
            error = str(e)

    return render(request, 'transactions/withdraw.html', {'currencies': currencies,'error': error})

#  ---------------------------------------------------------------------------------------


@login_required
def statement_view(request):
    account = BankAccount.objects.get(customer__user=request.user)
    transactions = Transaction.objects.filter(account=account).order_by('-created_at')

    return render(
        request,
        'transactions/statement.html',
        {'transactions': transactions}
    )

#  ---------------------------------------------------------------------------------------


@login_required
def transfer_request_view(request):
    from_account = BankAccount.objects.get(customer__user=request.user)
    # error = None
    currencies = Currency.objects.filter(is_active=True)


    if request.method == 'POST':
        to_account_number = request.POST.get('to_account')
        # amount = request.POST.get('amount')
        
        # ------------------- AMOUNT ------------------
        try:
            amount = Decimal(request.POST.get('amount'))
        except (TypeError, InvalidOperation):
            return render(
                request,
                'transactions/transfer.html',
                {'error': 'Invalid amount', 'currencies': currencies}
            )
        

        # ✅ NEW: currency from form
        # ---------------- Currency ----------------
        currency_code = request.POST.get('currency')
        try:
            currency = Currency.objects.get(code=currency_code)
        except Currency.DoesNotExist:
            return render(
                request,
                'transactions/transfer.html',
                {'error': 'Invalid currency selected', 'currencies': currencies}
            )
        
        # ---------------- Channel ----------------
        channel = request.POST.get('channel')

        if not channel:
            return render(
                request,
                'transactions/transfer.html',
                {'error': 'Transfer channel is required', 'currencies': currencies}
            )
        
        # ================= RTGS UI VALIDATION =================

        RTGS_MIN_AMOUNT = Decimal("200000.00")

        if channel == "RTGS" and currency.code == "INR":
            if amount < RTGS_MIN_AMOUNT:
                return render(
                    request,
                    'transactions/transfer.html',
                    {
                        'error': 'RTGS minimum transfer amount is ₹2,00,000',
                        'currencies': currencies
                    }
                )

        

        # =====================================================
        # ✅ FX / NON-FX CONSISTENCY VALIDATION (ADD HERE)
        # =====================================================
        BASE_CURRENCY = "INR"

        # FX can ONLY be used for foreign currency
        if channel == "FX" and currency.code == BASE_CURRENCY:
            return render(
                request,
                'transactions/transfer.html',
                {
                    'error': 'FX channel can only be used for foreign currency transfers',
                    'currencies': currencies
                }
            )

        # Foreign currency MUST use FX
        if channel != "FX" and currency.code != BASE_CURRENCY:
            return render(
                request,
                'transactions/transfer.html',
                {
                    'error': 'Foreign currency transfers must use FX channel',
                    'currencies': currencies
                }
            )

        # =====================================================
        # CONTINUE NORMAL FLOW
        # =====================================================

        # 1️⃣ Validate destination account
        try:
            to_account = BankAccount.objects.get(account_number=to_account_number)
        except BankAccount.DoesNotExist:
            return render(
                request,
                'transactions/transfer.html',
                {'error': 'Destination account not found', 'currencies': currencies}
            )
        

        # 2️⃣ Prevent self-transfer ✅ SELF-TRANSFER BLOCK (CORRECT PLACE) 
        if to_account == from_account:
            return render(
                request,
                'transactions/transfer.html',
                {'error': 'Cannot transfer to your own account', 'currencies': currencies}
            )
        
        # 3️⃣ DAILY TRANSFER LIMIT CHECK ✅ (CORRECT PLACE)
        today = now().date()

        daily_total = (
            TransferRequest.objects.filter(
                from_account=from_account,
                created_at__date=today,
                is_approved=True  # only approved transfers count
            ).aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )

        if daily_total + amount > DAILY_TRANSFER_LIMIT:
            return render(
                request,
                'transactions/transfer.html',
                {'error': 'Daily transfer limit exceeded', 'currencies': currencies}
            )


        # 4️⃣ Create transfer request ONLY after all checks pass ✅ CREATE TRANSFER REQUEST ONLY IF VALID  # 
        TransferRequest.objects.create(
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            currency=currency,
            channel=channel
        )

        # Audit logging
        log_action(
            user=request.user,
            action_type='TRANSFER',
            description=(
                f'Transfer requested from '
                f'{from_account.account_number} to '
                f'{to_account.account_number} '
                f'amount {amount} {currency.code} via {channel}'
            ),
            ip_address=get_client_ip(request)
        )

        return redirect('dashboard')

    return render(request, 'transactions/transfer.html', {'currencies': currencies})




#  ---------------------------------------------------------------------------------------


@login_required
def approve_transfer_view(request, transfer_id):
    transfer = TransferRequest.objects.get(id=transfer_id)

    approve_transfer(
        transfer=transfer,
        performed_by=request.user  # ✅ ADMIN USER PASSED
    )

    return redirect('/admin/transactions/transferrequest/')

#  ---------------------------------------------------------------------------------------


@login_required
def reverse_transaction_view(request, transaction_id):
    txn = Transaction.objects.get(id=transaction_id)

    reverse_transaction(
        transaction=txn,
        performed_by=request.user
    )

    return redirect('/admin/transactions/transaction/')

#  ---------------------------------------------------------------------------------------


# @login_required
# def transfer_history_view(request):
#     account = BankAccount.objects.get(customer__user=request.user)

#     transfers = TransferRequest.objects.filter(
#         from_account=account
#     ) | TransferRequest.objects.filter(
#         to_account=account
#     ).order_by('-created_at')

#     # transfers = transfers.order_by('-created_at')
#     return render(
#         request,
#         'transactions/transfer_history.html',
#         {'transfers': transfers}
#     )




@login_required
def transfer_history_view(request):
    account = BankAccount.objects.get(customer__user=request.user)

    transfers = TransferRequest.objects.filter(
        Q(from_account=account) | Q(to_account=account)
    ).select_related(
        'from_account',
        'to_account',
        'currency'
    ).order_by('-created_at')

    return render(
        request,
        'transactions/transfer_history.html',
        {'transfers': transfers, 'account': account}
    )

#  ---------------------------------------------------------------------------------------


@login_required
def user_transaction_history(request):
    account = BankAccount.objects.get(customer__user=request.user)

    transactions = (
        Transaction.objects
        .filter(account=account)
        .select_related('wallet', 'wallet__currency')
        .order_by('-created_at')
    )

    wallets = account.wallets.select_related('currency')

    return render(
        request,
        'transactions/statement.html',
        {
            'transactions': transactions,
            'wallets': wallets
        }
    )

#  ---------------------------------------------------------------------------------------


@login_required
def statement_pdf_view(request):
    account = BankAccount.objects.get(customer__user=request.user)
    txns = Transaction.objects.filter(account=account)

    pdf_file = generate_statement_pdf(txns, account.account_number)
    return FileResponse(open(pdf_file, 'rb'), as_attachment=True)


#  ---------------------------------------------------------------------------------------
