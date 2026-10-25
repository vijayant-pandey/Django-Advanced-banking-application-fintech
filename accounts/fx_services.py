import requests
from decimal import Decimal
from django.utils.timezone import now
from .models import Currency, FXRate

FX_API_URL = "https://open.er-api.com/v6/latest/"

def fetch_fx_rates(base_code='INR'):
    try:
        response = requests.get(
            f"{FX_API_URL}{base_code}",
            timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"FX API network error: {e}")

    data = response.json()

    # ✅ STRICT VALIDATION
    if data.get('result') != 'success':
        raise ValueError(f"FX API error response: {data}")

    if 'rates' not in data:
        raise ValueError(f"FX API malformed response: {data}")

    rates = data['rates']

    base_currency = Currency.objects.get(code=base_code)

    for code, rate in rates.items():
        try:
            target_currency = Currency.objects.get(code=code)
        except Currency.DoesNotExist:
            continue

        FXRate.objects.update_or_create(
            base_currency=base_currency,
            target_currency=target_currency,
            defaults={
                'rate': Decimal(str(rate)),
                'fetched_at': now()
            }
        )




FX_SPREAD_PERCENT = Decimal('0.50')  # 0.5%

def apply_fx_spread(rate):
    spread = rate * FX_SPREAD_PERCENT / Decimal('100')
    return rate - spread
