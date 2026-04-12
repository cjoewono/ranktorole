import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    TIER_CHOICES = [('free', 'Free'), ('pro', 'Pro')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    profile_context = models.JSONField(null=True, blank=True)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='free')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
