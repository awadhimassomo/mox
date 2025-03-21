from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
import uuid

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission

# Define region choices
REGION_CHOICES = [
    ('dar_es_salaam', 'Dar es Salaam'),
    ('arusha', 'Arusha'),
    ('mwanza', 'Mwanza'),
    ('dodoma', 'Dodoma'),
    ('tanga', 'Tanga'),
    ('mbeya', 'Mbeya'),
    ('morogoro', 'Morogoro'),
    ('zanzibar', 'Zanzibar'),
]

# Define user roles
ROLE_CHOICES = [
    ('customer', 'Customer'),
    ('business_owner', 'Business Owner'),
    ('rider', 'Rider'),
    ('operations', 'Operations'),
]

class CustomUserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('The Phone field must be set')
        
        # Normalize phone number
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        if not cleaned_phone.startswith('255'):
            if cleaned_phone.startswith('0'):
                cleaned_phone = '255' + cleaned_phone[1:]
            elif cleaned_phone.startswith('7'):
                cleaned_phone = '255' + cleaned_phone
        
        extra_fields.setdefault('is_active', True)  # Ensure active user
        user = self.model(phone=cleaned_phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'operations')  # Default superuser to operations
        return self.create_user(phone, password=password, **extra_fields)

class CustomUser(AbstractUser):
    username = None  # Remove username field
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(null=True, blank=True)
    region = models.CharField(max_length=50, choices=REGION_CHOICES, null=True, blank=True)
    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='customer')  # New Role Field
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_staff = models.BooleanField(default=False, null=True)
    is_active = models.BooleanField(default=True, null=True)
    is_superuser = models.BooleanField(default=False, null=True)
    date_joined = models.DateTimeField(default=timezone.now, null=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Add related_name to avoid clashes
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='operation_users'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='operation_users'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []  # Nothing required

    def __str__(self):
        return f"{self.phone} - {self.role}"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    region = models.CharField(max_length=50, choices=REGION_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.phone}'s Profile"


class Kijiwe(models.Model):
    """Pre-registered locations where riders operate from"""
    name = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=50, choices=REGION_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.name or "Unnamed Kijiwe"



class OTPCredit(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_credits')
    otp = models.CharField(max_length=5, null=True, blank=True)
    otp_timestamp = models.DateTimeField(null=True, blank=True)
    otp_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OTP for {self.user.phone} "

    def is_expired(self):
        if not self.otp_expiry:
            return True
        return timezone.now() > self.otp_expiry

    def can_resend(self):
        if not self.otp_timestamp:
            return True
        time_diff = timezone.now() - self.otp_timestamp
        return time_diff.seconds >= 60  # Allow resend after 60 seconds

    class Meta:
        unique_together = ('user',)
        verbose_name = 'OTP Credit'
        verbose_name_plural = 'OTP Credits'
