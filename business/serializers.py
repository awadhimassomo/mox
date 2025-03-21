from rest_framework import serializers
from .models import Business

class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            'id', 'name', 'owner_name', 'address', 'phone',
            'location', 'latitude', 'longitude', 'region',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
