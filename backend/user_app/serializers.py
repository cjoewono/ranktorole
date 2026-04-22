import re

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


def _derive_unique_username(email: str) -> str:
    base = re.sub(r'[^A-Za-z0-9._@+-]', '', email.split('@', 1)[0]) or 'user'
    candidate = base
    suffix = 2
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'profile_context', 'tier',
            'subscription_status',
            'resume_tailor_count', 'last_reset_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'tier',
            'subscription_status',
            'resume_tailor_count', 'last_reset_date',
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            username=_derive_unique_username(validated_data['email']),
            password=validated_data['password'],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        data['user'] = user
        return data
