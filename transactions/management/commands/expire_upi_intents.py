# from django.core.management.base import BaseCommand
# from django.utils.timezone import now
# from transactions.models import TransferRequest

# class Command(BaseCommand):
#     help = "Expire UPI intents past TTL"

#     def handle(self, *args, **kwargs):
#         expired = TransferRequest.objects.filter(
#             channel='UPI',
#             status='PENDING',
#             upi_intent_expires_at__lt=now()
#         )

#         count = expired.update(
#             status='EXPIRED',
#             upi_intent_status='EXPIRED'
#         )

#         self.stdout.write(f"Expired {count} UPI intents")


from django.core.management.base import BaseCommand
from django.utils.timezone import now

from transactions.models import TransferRequest
from audit.utils import log_action


class Command(BaseCommand):
    help = "Expire UPI intents that crossed expiry time"

    def handle(self, *args, **kwargs):
        # expired = TransferRequest.objects.filter(
        #     channel='UPI',
        #     status='PENDING',
        #     upi_intent_expires_at__lt=now()
        # )
        # ✅ QUERYSET DEFINED HERE
        qs = TransferRequest.objects.filter(
            channel='UPI',
            status='PENDING',
            upi_intent_expires_at__lt=now()
        )

        count = 0
        for transfer in qs:
            transfer.status = 'FAILED'
            transfer.upi_intent_status = 'EXPIRED'
            transfer.save(update_fields=['status', 'upi_intent_status'])

            log_action(
                user=None,
                action_type='UPI_INTENT_EXPIRED',
                description=f"UPI intent expired | Ref {transfer.reference_number}"
            )

            count += 1

        self.stdout.write(
            self.style.WARNING(f"Expired {count} UPI intents")
        )
