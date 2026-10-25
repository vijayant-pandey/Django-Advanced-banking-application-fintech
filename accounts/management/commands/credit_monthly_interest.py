from django.core.management.base import BaseCommand
from accounts.models import BankAccount
from accounts.services import credit_savings_interest

class Command(BaseCommand):
    help = "Credit monthly savings interest"

    def handle(self, *args, **kwargs):
        accounts = BankAccount.objects.filter(
            is_active=True,
            is_frozen=False
        )

        for account in accounts:
            credit_savings_interest(account)

        self.stdout.write("Monthly interest credited successfully")
