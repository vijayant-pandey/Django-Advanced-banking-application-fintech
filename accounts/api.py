from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import BankAccount

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_details_api(request):
    account = BankAccount.objects.get(customer__user=request.user)

    return Response({
        'account_number': account.account_number,
        'balance': str(account.balance),
        'status': 'ACTIVE' if account.is_active else 'INACTIVE'
    })
