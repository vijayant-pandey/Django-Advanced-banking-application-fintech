from django.core.management.base import BaseCommand
from accounts.models import BankAccount, Currency, Wallet

class Command(BaseCommand):
    help = "Create INR wallet for all existing bank accounts"

    def handle(self, *args, **kwargs):
        inr, _ = Currency.objects.get_or_create(
            code='INR',
            defaults={'name': 'Indian Rupee', 'symbol': '₹'}
        )

        for account in BankAccount.objects.all():
            wallet, created = Wallet.objects.get_or_create(
                bank_account=account,
                currency=inr,
                defaults={'balance': account.balance}
            )

            if created:
                self.stdout.write(
                    f"INR wallet created for {account.account_number}"
                )

        self.stdout.write("INR wallet setup completed")
