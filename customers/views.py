from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import BankAccount
from accounts.models import Wallet

# @login_required
# def dashboard(request):
#     account = None

#     try:
#         account = BankAccount.objects.get(customer__user=request.user)
#     except BankAccount.DoesNotExist:
#         pass

#     return render(
#         request,
#         'customers/dashboard.html',
#         {'account': account}
#     )


# @login_required
# def dashboard(request):
#     account = BankAccount.objects.filter(customer__user=request.user).first()
#     wallets = []

#     if account:
#         wallets = Wallet.objects.filter(bank_account=account)

#     return render(
#         request,
#         'customers/dashboard.html',
#         {
#             'account': account,
#             'wallets': wallets,
#         }
#     )

@login_required
def dashboard(request):
    account = BankAccount.objects.get(customer__user=request.user)
    wallets = Wallet.objects.filter(bank_account=account)

    return render(
        request,
        'customers/dashboard.html',
        {
            'account': account, 
            'wallets': wallets
        }
    )