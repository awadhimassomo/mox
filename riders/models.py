from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password

CustomUser = get_user_model()

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

class Rider(models.Model):
    # Transport type choices
    TRANSPORT_CHOICES = [
        ('boda', 'Boda'),
        ('guta', 'Guta'),
        ('kirikuu', 'Kirikuu'),
        ('kenta', 'Kenta'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='rider', null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    password = models.CharField(max_length=128, null=True, blank=True)  # For storing hashed password
    region = models.CharField(max_length=50, choices=REGION_CHOICES, null=True, blank=True)
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_CHOICES, null=True, blank=True, help_text='Type of transport vehicle used by the rider',default='boda')
    kijiwe = models.ForeignKey('operations.Kijiwe', on_delete=models.SET_NULL, null=True, blank=True)
    is_available = models.BooleanField(default=True, null=True, blank=True)
    consecutive_declines = models.IntegerField(default=0, null=True, blank=True)
    last_decline_time = models.DateTimeField(null=True, blank=True)
    block_until = models.DateTimeField(null=True, blank=True)
    penalties = models.IntegerField(default=0, help_text='Number of penalties for missing orders', null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(null=True, blank=True, help_text='Human-readable address from reverse geocoding')
    last_location_update = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    # Profile image field
    profile_image = models.ImageField(upload_to='riders/profile_images/', null=True, blank=True,
                                     help_text='Profile photo of the rider')
    
    # Image fields for verification documents
    id_photo = models.ImageField(upload_to='riders/id_photos/', null=True, blank=True, 
                                help_text='National ID or Voter\'s card')
    latra_certificate = models.ImageField(upload_to='riders/latra/', null=True, blank=True,
                                        help_text='Land Transport Regulatory Authority certificate')
    insurance_certificate = models.ImageField(upload_to='riders/insurance/', null=True, blank=True,
                                            help_text='Vehicle insurance certificate')
    vehicle_photo = models.ImageField(upload_to='riders/vehicles/', null=True, blank=True,
                                    help_text='Photo of the delivery vehicle')
    license_photo = models.ImageField(upload_to='riders/licenses/', null=True, blank=True,
                                    help_text='Driver\'s license photo')

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.phone_number or "Unnamed Rider"

    def save(self, *args, **kwargs):
        # Hash the password if it's being set for the first time or changed
        if self.password and not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def can_receive_orders(self):
        if not self.block_until:
            return True
        return timezone.now() >= self.block_until
    
    def handle_decline(self):
        current_time = timezone.now()
        
        # Reset consecutive declines if last decline was more than 1 hour ago
        if self.last_decline_time and (current_time - self.last_decline_time) > timedelta(hours=1):
            self.consecutive_declines = 0
        
        self.consecutive_declines += 1
        self.last_decline_time = current_time
        
        # Apply blocks based on consecutive declines
        if self.consecutive_declines >= 5:
            self.block_until = current_time + timedelta(hours=24)
        elif self.consecutive_declines >= 3:
            self.block_until = current_time + timedelta(hours=6)
        
        self.save()

class RiderPenalty(models.Model):
    """
    Model for tracking penalties when riders don't respond to gas delivery orders within time limits.
    """
    PENALTY_TYPES = [
        ('MISSED_ORDER', 'Missed Order'),
        ('LATE_PICKUP', 'Late Pickup'),
        ('LATE_DELIVERY', 'Late Delivery'),
        ('OTHER', 'Other'),
    ]
    
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='penalty_records')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='rider_penalties')
    penalty_type = models.CharField(max_length=20, choices=PENALTY_TYPES, default='OTHER')
    description = models.TextField(blank=True)
    points = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Rider Penalty'
        verbose_name_plural = 'Rider Penalties'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rider} - {self.get_penalty_type_display()} - {self.created_at.strftime('%d/%m/%Y')}"

class RiderPenaltyOld(models.Model):
    PENALTY_TYPES = [
        ('late_delivery', 'Late Delivery'),
        ('order_decline', 'Order Decline'),
        ('order_cancel', 'Order Cancellation'),
        ('complaint', 'Customer Complaint'),
        ('other', 'Other')
    ]
    
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name='penalty_records_old', null=True, blank=True)
    type = models.CharField(max_length=20, choices=PENALTY_TYPES, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    resolved = models.BooleanField(default=False, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Rider Penalties'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rider} - {self.get_type_display()} - {self.created_at.date()}"

    def resolve(self, user, note=None):
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        if note:
            self.resolution_note = note
        self.save()

@receiver(post_save, sender=Rider)
def create_user_for_rider(sender, instance, created, **kwargs):
    """Create a User instance for the Rider if it doesn't exist"""
    if created and not instance.user:
        # Create a User instance
        username = instance.phone_number  # Use phone number as username
        user = CustomUser.objects.create_user(
            phone=username,
            email=instance.email,
            password=instance.password,  # This will be hashed by Django
            first_name=instance.first_name,
            last_name=instance.last_name
        )
        # Link the User to the Rider
        instance.user = user
        instance.save()
        
        
# Add to models.py if it doesn't exist
class RiderOtp(models.Model):
    """Model for storing OTP information for rider verification"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=10)
    otp_timestamp = models.DateTimeField(auto_now=True)
    otp_expiry = models.DateTimeField()
    
    class Meta:
        verbose_name = 'Rider OTP'
        verbose_name_plural = 'Rider OTPs'
    
    def __str__(self):
        return f"OTP for {self.user.phone}"
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return timezone.now() <= self.otp_expiry
