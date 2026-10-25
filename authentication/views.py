from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegisterForm
from accounts.models import BankAccount
from accounts.utils import generate_account_number
from audit.utils import log_action
from audit.helpers import get_client_ip

from customers.models import Customer


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            customer = Customer.objects.create(
                user=user,
                phone='',
                address=''
            )

            BankAccount.objects.create(
                customer=customer,
                account_number=generate_account_number(),
                account_type='SAVINGS',
                balance=0.00,
                is_active=False   # admin must approve
            )

            login(request, user)

            log_action(
                user=request.user,
                action_type='LOGIN',
                description='User logged in',
                ip_address=get_client_ip(request)
            )
            
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'authentication/register.html', {'form': form})
