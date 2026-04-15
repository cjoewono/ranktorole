from django.urls import path

from .billing_views import (
    BillingStatusView,
    CheckoutSessionView,
    PortalSessionView,
    StripeWebhookView,
)

urlpatterns = [
    path('checkout/', CheckoutSessionView.as_view(), name='billing-checkout'),
    path('portal/', PortalSessionView.as_view(), name='billing-portal'),
    path('status/', BillingStatusView.as_view(), name='billing-status'),
    path('webhook/', StripeWebhookView.as_view(), name='billing-webhook'),
]
