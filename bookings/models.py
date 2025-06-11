from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings

# Get the custom user model
CustomUser = get_user_model()

# Import Rider model from the operations app
Rider = CustomUser

class ServiceType(models.Model):
    """Model for different types of bookable services"""
    SERVICE_CHOICES = [
        ('moving_truck', 'Moving Truck'),
        ('water_bowser', 'Water Bowser'),
        ('sewage_truck', 'Sewage Truck'),
        ('ambulance', 'Ambulance'),
        ('fuel_truck', 'Fuel Truck'),
        ('other', 'Other')
    ]
    
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, choices=SERVICE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_per_km = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Service Type'
        verbose_name_plural = 'Service Types'
        ordering = ['name']


class ServiceBooking(models.Model):
    """Model for service bookings"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    booking_number = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='service_bookings')
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name='bookings')
    rider = models.ForeignKey(Rider, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
    
    # Location details
    pickup_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    destination_address = models.TextField()
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Service details
    scheduled_date = models.DateTimeField()
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2, default=1.0,
                                       validators=[MinValueValidator(0.5)])
    notes = models.TextField(blank=True)
    
    # Status and pricing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.booking_number} - {self.service_type.name}"
    
    def clean(self):
        if self.scheduled_date < timezone.now():
            raise ValidationError({
                'scheduled_date': 'Scheduled date cannot be in the past.'
            })
    
    def save(self, *args, **kwargs):
        if not self.booking_number:
            # Generate booking number: B + timestamp + random 4 digits
            import random
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_suffix = str(random.randint(1000, 9999))
            self.booking_number = f"B{timestamp}{random_suffix}"
        
        # Calculate total price if not set
        if not self.total_price and self.service_type:
            distance_cost = float(self.distance_km or 0) * float(self.service_type.price_per_km)
            self.total_price = float(self.service_type.base_price) + distance_cost
            
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Service Booking'
        verbose_name_plural = 'Service Bookings'


class RiderServicePreference(models.Model):
    """Model to store rider's service preferences and availability"""
    rider = models.OneToOneField(Rider, on_delete=models.CASCADE, related_name='service_preferences')
    services = models.ManyToManyField(ServiceType, related_name='service_riders')
    is_available = models.BooleanField(default=True)
    working_hours_start = models.TimeField(default='08:00')
    working_hours_end = models.TimeField(default='17:00')
    working_days = models.CharField(max_length=50, default='1,2,3,4,5',
                                  help_text='Comma-separated list of weekdays (1=Monday, 7=Sunday)')
    service_radius_km = models.PositiveIntegerField(default=20, help_text='Maximum service radius in kilometers')
    
    def __str__(self):
        return f"{self.rider} - Service Preferences"
    
    class Meta:
        verbose_name = 'Rider Service Preference'
        verbose_name_plural = 'Rider Service Preferences'
