from rest_framework import serializers
from .models import Resume


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = [
            'id', 'military_text', 'job_description',
            'civilian_title', 'summary', 'bullets',
            'session_anchor', 'approved_bullets', 'rejected_bullets',
            'is_finalized', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'session_anchor']


class TranslationInputSerializer(serializers.Serializer):
    military_text = serializers.CharField(min_length=10, max_length=5000)
    job_description = serializers.CharField(min_length=10, max_length=5000)


class TranslationOutputSerializer(serializers.Serializer):
    civilian_title = serializers.CharField()
    summary = serializers.CharField()
    bullets = serializers.ListField(child=serializers.CharField())


class FinalizeInputSerializer(serializers.Serializer):
    civilian_title = serializers.CharField(required=False)
    summary = serializers.CharField(required=False)
    bullets = serializers.ListField(child=serializers.CharField(), required=False)
