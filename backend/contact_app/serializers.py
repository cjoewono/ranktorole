from rest_framework import serializers
from .models import Contact


class ContactSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField(max_length=254)
    company = serializers.CharField(max_length=200)
    role = serializers.CharField(max_length=200)
    notes = serializers.CharField(max_length=5000, required=False, allow_blank=True)

    class Meta:
        model = Contact
        fields = [
            'id', 'name', 'email', 'company', 'role', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
