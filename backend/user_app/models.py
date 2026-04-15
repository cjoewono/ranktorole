import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    TIER_CHOICES = [('free', 'Free'), ('pro', 'Pro')]

    SUBSCRIPTION_STATUS_CHOICES = [
        ('inactive', 'Inactive'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('trialing', 'Trialing'),
        ('unpaid', 'Unpaid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    profile_context = models.JSONField(null=True, blank=True)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='free')

    # --- Billing (no PAN/CVV — Stripe-side tokens only) ---
    stripe_customer_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    subscription_status = models.CharField(
        max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='inactive'
    )

    # --- Daily usage counters (reset at UTC midnight on first hit) ---
    resume_tailor_count = models.PositiveIntegerField(default=0)
    last_reset_date = models.DateField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'

    def __str__(self) -> str:
        return f"{self.email} ({self.tier})"


class SubscriptionAuditLog(models.Model):
    """Immutable audit trail for financial/regulatory compliance.

    One row per subscription state transition. Never updated or deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='subscription_audit_logs',
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    stripe_event_id = models.CharField(max_length=128, unique=True, db_index=True)
    event_type = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        db_table = 'subscription_audit_logs'
        ordering = ['-timestamp']

    def __str__(self) -> str:
        return f"{self.user_id} {self.previous_status}→{self.new_status} @{self.timestamp:%Y-%m-%d}"
