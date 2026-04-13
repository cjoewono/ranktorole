from rest_framework import serializers
from .models import Resume


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = [
            'id', 'military_text', 'job_description',
            'civilian_title', 'summary', 'bullets',
            'roles', 'chat_history', 'ai_initial_draft',
            'session_anchor', 'approved_bullets', 'rejected_bullets',
            'is_finalized', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'session_anchor', 'ai_initial_draft']


class RoleEntrySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    org = serializers.CharField(max_length=200)
    dates = serializers.CharField(max_length=100)
    bullets = serializers.ListField(
        child=serializers.CharField(max_length=500),
        max_length=10,
    )


class FinalizeInputSerializer(serializers.Serializer):
    civilian_title = serializers.CharField(required=False, max_length=200)
    summary = serializers.CharField(required=False, max_length=3000)
    roles = serializers.ListField(
        child=RoleEntrySerializer(),
        required=False,
        max_length=20,
    )
    # Keep bullets for backward compatibility with existing tests
    bullets = serializers.ListField(child=serializers.CharField(), required=False)


class DraftInputSerializer(serializers.Serializer):
    job_description = serializers.CharField(
        min_length=10,
        max_length=15000,
        required=False,
        allow_blank=True,
    )
