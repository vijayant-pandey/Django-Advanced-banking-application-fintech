from django.core.management.base import BaseCommand
from django.utils.timezone import now
from transactions.settlement_engine import dispatch_settlement
from transactions.models import TransferRequest 
from transactions.services import settle_transfer
from transactions.settlement_engine import is_neft_window_open

# class Command(BaseCommand):
#     help = "Settle pending NEFT transfers"

#     def handle(self, *args, **kwargs):

#         # 🆕 Generate NEFT batch ID (RBI-style)
#         batch_id = now().strftime("NEFT-%Y%m%d-%H%M")

#         qs = TransferRequest.objects.filter(
#             channel='NEFT',
#             status='PENDING',
#             is_approved=True
#         )

#         if not qs.exists():
#             self.stdout.write("No pending NEFT transfers.")
#             return

#         for transfer in qs:
#             transfer.neft_batch_id = batch_id
#             transfer.save(update_fields=['neft_batch_id'])

#             dispatch_settlement(transfer)

#         self.stdout.write(
#             f"Settled {qs.count()} NEFT transfers in batch {batch_id}"
#         )






class Command(BaseCommand):
    help = "Settle pending NEFT transfers (RBI window aware)"

    def handle(self, *args, **kwargs):

        if not is_neft_window_open():
            self.stdout.write(
                self.style.WARNING(
                    "❌ NEFT window closed (09:00–19:00). Settlement aborted."
                )
            )
            return

        batch_id = now().strftime("NEFT-%Y%m%d-%H%M")

        qs = TransferRequest.objects.filter(
            channel='NEFT',
            status='PENDING'
        )

        if not qs.exists():
            self.stdout.write("No pending NEFT transfers.")
            return

        count = 0
        for transfer in qs:
            transfer.neft_batch_id = batch_id
            settle_transfer(transfer)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Settled {count} NEFT transfers in batch {batch_id}"
            )
        )

