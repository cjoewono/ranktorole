from django.contrib import admin
from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'civilian_title', 'created_at']
    list_filter = ['user']
    search_fields = ['civilian_title', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
