from rest_framework import serializers
from .models import Rider, RiderPenalty

class RiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rider
        fields = [
            'id', 'first_name', 'last_name', 'phone_number',
            'email', 'region', 'is_available', 'latitude',
            'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class RiderPenaltySerializer(serializers.ModelSerializer):
    class Meta:
        model = RiderPenalty
        fields = [
            'id', 'rider', 'type', 'reason', 'created_at',
            'resolved', 'resolved_at', 'resolved_by', 'resolution_note'
        ]
        read_only_fields = ['created_at', 'resolved_at']
