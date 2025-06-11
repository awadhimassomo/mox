from rest_framework import serializers
from .models import ServiceType, ServiceBooking, RiderServicePreference
from operations.models import CustomUser

# Import Rider model
Rider = CustomUser

# Simple rider serializer for the booking system
class RiderSerializer(serializers.ModelSerializer):
    is_available = serializers.BooleanField(source='rider.is_available', read_only=True)
    
    class Meta:
        model = Rider
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'is_available']
        read_only_fields = ('id', 'is_available')

class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer using the CustomUser model from operations app"""
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone']
        read_only_fields = ('id',)

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class RiderServicePreferenceSerializer(serializers.ModelSerializer):
    services = ServiceTypeSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=ServiceType.objects.all(),
        source='services',
        required=False
    )
    
    class Meta:
        model = RiderServicePreference
        fields = [
            'id', 'rider', 'services', 'service_ids', 'is_available',
            'working_hours_start', 'working_hours_end', 'working_days',
            'service_radius_km', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Remove the write-only field from the response
        representation.pop('service_ids', None)
        return representation

class ServiceBookingSerializer(serializers.ModelSerializer):
    service_type = ServiceTypeSerializer(read_only=True)
    service_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ServiceType.objects.filter(is_active=True),
        source='service_type',
        write_only=True
    )
    customer = UserSerializer(read_only=True)
    rider = RiderSerializer(read_only=True)
    rider_id = serializers.PrimaryKeyRelatedField(
        queryset=Rider.objects.all(),  # We'll filter available riders in the view
        source='rider',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter available riders when the field is in the request
        if 'request' in self.context and self.context['request'].method in ['POST', 'PUT', 'PATCH']:
            # Get the queryset of available riders
            available_riders = Rider.objects.filter(
                is_active=True,
                rider__is_available=True  # Using the reverse relation from CustomUser to Rider
            )
            self.fields['rider_id'].queryset = available_riders
    
    class Meta:
        model = ServiceBooking
        fields = [
            'id', 'booking_number', 'customer', 'service_type', 'service_type_id',
            'rider', 'rider_id', 'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'destination_address', 'destination_latitude', 'destination_longitude',
            'scheduled_date', 'duration_hours', 'notes', 'status', 'base_price',
            'distance_km', 'total_price', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = (
            'id', 'booking_number', 'customer', 'created_at', 'updated_at',
            'status', 'total_price'
        )
    
    def validate_scheduled_date(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("Scheduled date cannot be in the past.")
        return value
    
    def create(self, validated_data):
        # Set the current user as the customer
        validated_data['customer'] = self.context['request'].user
        return super().create(validated_data)

class ServiceBookingStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ServiceBooking.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        if 'notes' in validated_data:
            if instance.notes:
                instance.notes += f"\n--- Status Changed to {instance.status} ---\n{validated_data['notes']}"
            else:
                instance.notes = f"--- Status Changed to {instance.status} ---\n{validated_data['notes']}"
        
        # Update completed_at if status is completed
        if instance.status == 'completed' and not instance.completed_at:
            from django.utils import timezone
            instance.completed_at = timezone.now()
            
        instance.save()
        return instance
