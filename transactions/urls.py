from django.urls import path
from .views import deposit_view, withdraw_view, statement_view, transfer_request_view, transfer_history_view, user_transaction_history
from transactions.admin_views import admin_dashboard
from transactions.webhooks.upi import upi_psp_webhook

urlpatterns = [
    path('deposit/', deposit_view, name='deposit'),
    path('withdraw/', withdraw_view, name='withdraw'),
    path('statement/', statement_view, name='statement'),
    path('statement/', user_transaction_history, name='transaction_statement'),
    path('transfer/', transfer_request_view, name='transfer'),
    path('transfers/history/', transfer_history_view, name='transfer_history'),
    path("dashboard/admin/", admin_dashboard, name="admin-dashboard"),
    path("webhooks/upi/", upi_psp_webhook, name="upi_psp_webhook"),



]


# UPI-5D96085F7BAC

