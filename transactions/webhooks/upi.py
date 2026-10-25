import hmac
import hashlib
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from transactions.models import TransferRequest
from transactions.settlement_engine import dispatch_settlement
from audit.utils import log_action


# 🔐 Mock PSP secret
UPI_PSP_SECRET = b"mock_psp_secret_key"


def verify_signature(payload, signature):
    expected = hmac.new(
        UPI_PSP_SECRET,
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@csrf_exempt
def upi_psp_webhook(request):
    """
    Simulated PSP callback:
    {
        "reference_number": "UPI-XXXX",
        "status": "SUCCESS" | "FAILED"
    }
    """

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    payload = request.body
    signature = request.headers.get("X-PSP-SIGNATURE")

    if not signature or not verify_signature(payload, signature):
        return JsonResponse({"error": "Invalid signature"}, status=403)

    data = json.loads(payload)
    ref = data.get("reference_number")
    status = data.get("status")

    try:
        transfer = TransferRequest.objects.get(
            reference_number=ref,
            channel='UPI'
        )
    except TransferRequest.DoesNotExist:
        return JsonResponse({"error": "Transfer not found"}, status=404)

    # 🚫 Expired guard
    if transfer.upi_intent_expires_at and now() > transfer.upi_intent_expires_at:
        return JsonResponse({"error": "UPI intent expired"}, status=409)

    if status == "SUCCESS":
        transfer.status = 'APPROVED'
        transfer.upi_intent_status = 'APPROVED'
        transfer.save(update_fields=['status', 'upi_intent_status'])

        dispatch_settlement(transfer)

        log_action(
            user=None,
            action_type='UPI_PSP_SUCCESS',
            description=f"UPI PSP success | Ref {transfer.reference_number}"
        )

        return JsonResponse({"message": "UPI settled"})

    if status == "FAILED":
        transfer.status = 'FAILED'
        transfer.upi_intent_status = 'FAILED'
        transfer.save(update_fields=['status', 'upi_intent_status'])

        log_action(
            user=None,
            action_type='UPI_PSP_FAILED',
            description=f"UPI PSP failed | Ref {transfer.reference_number}"
        )

        return JsonResponse({"message": "UPI failed"})

    return JsonResponse({"error": "Invalid status"}, status=400)
