

from django.urls import path
from django.contrib.auth import views as auth_views
from accounts.api import account_details_api
from .views import register_view

urlpatterns = [
    path('api/account/', account_details_api),
]



