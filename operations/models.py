from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
import re
import uuid

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

def normalize_phone_number(phone):
    """
    Normalize a phone number to the standard E.164 format for Tanzania (255XXXXXXXXX)
    
    Args:
        phone: The phone number to normalize
        
    Returns:
        Normalized phone number string
        
    Raises:
        ValidationError: If the phone number is invalid
    """
    if not phone:
        raise ValidationError("Phone number cannot be empty")
        
    # Remove any non-digit characters
    cleaned_phone = ''.join(filter(str.isdigit, str(phone)))
    
    # Handle different formats
    if cleaned_phone.startswith('255'):
        # Already in correct format
        pass
    elif cleaned_phone.startswith('0'):
        # Convert 0XXX... to 255XXX...
        cleaned_phone = '255' + cleaned_phone[1:]
    elif cleaned_phone.startswith('+255'):
        # Remove + if present
        cleaned_phone = cleaned_phone[1:]
    elif cleaned_phone.startswith('7') or cleaned_phone.startswith('6'):
        # Format starting with 7 or 6 (common in Tanzania)
        if len(cleaned_phone) == 9:  # 7XXXXXXXX or 6XXXXXXXX
            cleaned_phone = '255' + cleaned_phone
        else:
            raise ValidationError("Invalid phone number format")
    else:
        raise ValidationError("Invalid phone number format for Tanzania")
    
    # Verify the length for Tanzania numbers
    if len(cleaned_phone) != 12:  # 255 + 9 digits
        raise ValidationError(f"Phone number must be 12 digits for Tanzania (255XXXXXXXXX), got {len(cleaned_phone)}")
    
    # Validate the pattern for Tanzania numbers
    if not re.match(r'^255[67]\d{8}$', cleaned_phone):
        raise ValidationError("Phone number must start with 255 followed by 6 or 7 and 8 more digits")
        
    return cleaned_phone

def validate_phone_number(phone):
    """
    Validate a phone number for Tanzania
    
    Args:
        phone: The phone number to validate
        
    Raises:
        ValidationError: If the phone number is invalid
    """
    try:
        normalize_phone_number(phone)
    except ValidationError as e:
        raise e

class CustomUserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        """
        Create and save a user with the given phone number and password.
        """
        if not phone:
            raise ValueError('The Phone field must be set')
        
        try:
            # Normalize phone number using our utility function
            normalized_phone = normalize_phone_number(phone)
        except ValidationError as e:
            raise ValueError(f"Invalid phone number: {str(e)}")
        
        # If a password is provided, validate it
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValueError(f"Password validation failed: {', '.join(e.messages)}")
        
        extra_fields.setdefault('is_active', True)
        user = self.model(phone=normalized_phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """
        Create and save a superuser with the given phone number and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'operations')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(phone, password=password, **extra_fields)

    def get_by_phone(self, phone):
        """
        Get a user by phone number, attempting different formats if the exact match fails.
        This is useful for authentication where users might enter their phone in various formats.
        """
        try:
            normalized_phone = normalize_phone_number(phone)
            return self.get(phone=normalized_phone)
        except (self.model.DoesNotExist, ValidationError):
            # Try various formats as fallbacks
            fallback_formats = []
            
            # Clean the phone number first
            cleaned_phone = ''.join(filter(str.isdigit, str(phone)))
            
            if cleaned_phone.startswith('255'):
                # Try format with leading zero
                fallback_formats.append('0' + cleaned_phone[3:])
                # Try with plus
                fallback_formats.append('+' + cleaned_phone)
            elif cleaned_phone.startswith('0'):
                # Try without leading zero
                fallback_formats.append('255' + cleaned_phone[1:])
            elif cleaned_phone.startswith('7') or cleaned_phone.startswith('6'):
                # Try with country code
                fallback_formats.append('255' + cleaned_phone)
                
            # Try all fallback formats
            for format in fallback_formats:
                try:
                    return self.get(phone=normalize_phone_number(format))
                except (self.model.DoesNotExist, ValidationError):
                    continue
                    
            # If we get here, no match was found
            raise self.model.DoesNotExist("User with this phone number does not exist")

class CustomUser(AbstractUser):
    username = None  # Remove username field
    phone = models.CharField(
        max_length=15, 
        unique=True, 
        validators=[validate_phone_number],
        help_text="Phone number in international format (e.g., 255XXXXXXXXX)"
    )
    email = models.EmailField(null=True, blank=True)
    region = models.CharField(max_length=50, choices=REGION_CHOICES, null=True, blank=True)
    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='customer')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_staff = models.BooleanField(default=False, null=True)
    is_active = models.BooleanField(default=True, null=True)
    is_superuser = models.BooleanField(default=False, null=True)
    date_joined = models.DateTimeField(default=timezone.now, null=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Security-related fields
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    password_reset_token = models.CharField(max_length=100, null=True, blank=True)
    password_reset_token_expiry = models.DateTimeField(null=True, blank=True)

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
        
    def save(self, *args, **kwargs):
        # Ensure phone number is normalized before saving
        if self.phone:
            try:
                self.phone = normalize_phone_number(self.phone)
            except ValidationError:
                # If we can't normalize during a save, keep existing value
                # This should be caught by form validation before reaching here
                pass
        super().save(*args, **kwargs)
    
    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        If neither is available, return the phone number.
        """
        if self.first_name and self.last_name:
            full_name = f"{self.first_name} {self.last_name}"
            return full_name.strip()
        return self.phone
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name if self.first_name else self.phone
        
    def increment_failed_login(self):
        """Increment the failed login attempts counter and lock account if needed"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock the account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            # Lock for 30 minutes
            self.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
            
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])
    
    def reset_failed_login(self):
        """Reset the failed login attempts counter"""
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.account_locked_until = None
            self.save(update_fields=['failed_login_attempts', 'account_locked_until'])
    
    def is_account_locked(self):
        """Check if the account is currently locked"""
        if not self.account_locked_until:
            return False
        return timezone.now() < self.account_locked_until

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
