from django.contrib import admin
from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'role', 'user']
    list_filter = ['user']
    search_fields = ['name', 'email', 'company']
    readonly_fields = ['id', 'created_at', 'updated_at']
