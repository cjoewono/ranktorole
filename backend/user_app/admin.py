from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import SubscriptionAuditLog, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'tier', 'subscription_status', 'is_staff', 'created_at']
    list_filter = ['tier', 'subscription_status', 'is_staff', 'is_active']
    search_fields = ['email', 'username', 'stripe_customer_id']
    ordering = ['-created_at']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('RankToRole', {'fields': ('tier', 'profile_context')}),
        ('Billing', {'fields': (
            'stripe_customer_id', 'subscription_status',
            'resume_tailor_count', 'last_reset_date',
        )}),
    )
    readonly_fields = ('stripe_customer_id',)


@admin.register(SubscriptionAuditLog)
class SubscriptionAuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'previous_status', 'new_status', 'event_type', 'stripe_event_id']
    list_filter = ['event_type', 'new_status']
    search_fields = ['user__email', 'stripe_event_id']
    readonly_fields = ['id', 'user', 'timestamp', 'previous_status', 'new_status', 'stripe_event_id', 'event_type']
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
