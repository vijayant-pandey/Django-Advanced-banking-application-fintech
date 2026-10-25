from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', include('transactions.urls')), 
    path('auth/', include('authentication.urls')),
    path('transactions/', include('transactions.urls')),
    path('', include('customers.urls')),
]

