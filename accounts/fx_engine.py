# from decimal import Decimal
# from accounts.models import FXRate, Currency


# class FXEngine:
#     BASE_CURRENCY = 'INR'

#     @staticmethod
#     def get_rate(from_currency, to_currency):
#         """
#         Returns Decimal FX rate
#         """

#         if from_currency == to_currency:
#             return Decimal('1.00')

#         from_cur = Currency.objects.get(code=from_currency)
#         to_cur = Currency.objects.get(code=to_currency)

#         # Direct rate
#         try:
#             fx = FXRate.objects.get(
#                 base_currency=from_cur,
#                 target_currency=to_cur
#             )
#             return fx.rate
#         except FXRate.DoesNotExist:
#             pass

#         # Reverse rate
#         try:
#             fx = FXRate.objects.get(
#                 base_currency=to_cur,
#                 target_currency=from_cur
#             )
#             return Decimal('1.00') / fx.rate
#         except FXRate.DoesNotExist:
#             raise ValueError("FX rate not available")



from decimal import Decimal
from accounts.models import FXRate, Currency


class FXEngine:
    BASE_CURRENCY = 'INR'
    DEFAULT_SPREAD_PERCENT = Decimal('0.50')  # 0.5%

    @staticmethod
    def get_rate(from_currency, to_currency):
        if from_currency == to_currency:
            return Decimal('1.00')

        from_cur = Currency.objects.get(code=from_currency)
        to_cur = Currency.objects.get(code=to_currency)

        # Direct rate
        try:
            fx = FXRate.objects.get(
                base_currency=from_cur,
                target_currency=to_cur
            )
            return fx.rate
        except FXRate.DoesNotExist:
            pass

        # Reverse rate
        try:
            fx = FXRate.objects.get(
                base_currency=to_cur,
                target_currency=from_cur
            )
            return Decimal('1.00') / fx.rate
        except FXRate.DoesNotExist:
            raise ValueError("FX rate not available")

    @staticmethod
    def apply_spread(rate, spread_percent=None):
        spread = spread_percent or FXEngine.DEFAULT_SPREAD_PERCENT
        return rate * (Decimal('1.00') + spread / Decimal('100'))
    

    @staticmethod
    def convert(amount, from_currency, to_currency):
        amount = Decimal(amount)
        rate = FXEngine.get_rate(from_currency, to_currency)
        rate_with_spread = FXEngine.apply_spread(rate)
        converted_amount = amount * rate_with_spread
        return converted_amount.quantize(Decimal('0.01'))

    @staticmethod
    def convert_with_details(amount, from_currency, to_currency):
        amount = Decimal(amount)

        base_rate = FXEngine.get_rate(from_currency, to_currency)
        final_rate = FXEngine.apply_spread(base_rate)

        converted_amount = (amount * final_rate).quantize(Decimal('0.01'))
        spread_amount = ((final_rate - base_rate) * amount).quantize(Decimal('0.01'))

        return {
            'base_rate': base_rate,
            'final_rate': final_rate,
            'converted_amount': converted_amount,
            'spread_amount': spread_amount,
        }