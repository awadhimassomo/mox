import logging
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import CustomerProfile
from operations.models import UserProfile

# Configure logger
logger = logging.getLogger(__name__)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name',
            'region', 'created_at', 'updated_at', 'is_active',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['created_at', 'updated_at', 'date_joined', 'last_login']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'phone', 'region',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = '__all__'


class CustomerLoginSerializer(serializers.Serializer):
    """
    Serializer for customer login.
    """
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        if phone_number and password:
            # Ensure phone number is in the correct format
            phone_number = str(phone_number).strip()
            if not phone_number.startswith('255'):
                if phone_number.startswith('0'):
                    phone_number = '255' + phone_number[1:]
                elif phone_number.startswith('+'):
                    phone_number = phone_number[1:]
            
            logger.debug(f"Attempting to authenticate user with phone: {phone_number}")
            user = authenticate(request=self.context.get('request'), 
                             username=phone_number, 
                             password=password)
            
            if not user:
                msg = 'Unable to log in with provided credentials.'
                logger.warning(f"Authentication failed for phone: {phone_number}")
                raise serializers.ValidationError({'non_field_errors': [msg]}, code='authorization')
            
            if not user.is_active:
                msg = 'User account is disabled.'
                logger.warning(f"Login attempt for inactive user: {phone_number}")
                raise serializers.ValidationError({'non_field_errors': [msg]}, code='authorization')
                
            attrs['user'] = user
            return attrs
        
        msg = 'Must include "phone_number" and "password".'
        logger.warning(f"Missing required fields in login request: {attrs}")
        raise serializers.ValidationError({'non_field_errors': [msg]}, code='authorization')
