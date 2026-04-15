from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class CheckoutThrottle(UserRateThrottle):
    """Prevent card-testing / botting on the checkout endpoint."""
    scope = 'billing_checkout'


class CheckoutAnonThrottle(AnonRateThrottle):
    scope = 'billing_checkout'
