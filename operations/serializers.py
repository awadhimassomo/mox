from rest_framework import serializers
from .models import  Kijiwe, CustomUser, UserProfile
from riders.serializers import RiderSerializer
from business.serializers import BusinessSerializer

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'phone', 'email', 'first_name', 'last_name', 'region')
        read_only_fields = ('id',)

class UserProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'region', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')



class KijiweSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kijiwe
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')



class SendOTPSerializer(serializers.Serializer):
    personal_number = serializers.CharField(required=True)
    business_id = serializers.IntegerField(required=True)

class ResendOTPSerializer(serializers.Serializer):
    phoneNumber = serializers.CharField(required=True)

class VerifyOTPSerializer(serializers.Serializer):
    personal_number = serializers.CharField(required=True)
    business_id = serializers.IntegerField(required=True)
    otp = serializers.CharField(required=True)
