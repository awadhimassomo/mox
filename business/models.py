from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from operations.models import CustomUser

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



class Business(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="businesses", null=True, blank=True)  # Link to user
    name = models.CharField(max_length=255, null=True, blank=True)
    owner_name = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    region = models.CharField(max_length=50, choices=REGION_CHOICES, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    cover_image = models.ImageField(upload_to='business/covers/', null=True, blank=True)
    banner = models.ImageField(upload_to='business/banners/', null=True, blank=True, help_text="Banner image displayed on the business page")
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.user.phone if self.user else 'No Owner'}"

    class Meta:
        verbose_name_plural = 'Businesses'
        ordering = ['name']

class Product(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('l', 'Liters'),
        ('ml', 'Milliliters'),
        ('pcs', 'Pieces'),
        ('pkg', 'Package'),
    ]

    # Basic product information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pcs')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    
    # Gas specific fields (only used if category is 'gas')
    gas_type = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('lpg', 'LPG'),
        ('natural', 'Natural Gas'),
        ('propane', 'Propane'),
        ('butane', 'Butane'),
    ])
    tank_size = models.IntegerField(blank=True, null=True, choices=[
        (6, '6 KG'),
        (13, '13 KG'),
        (15, '15 KG'),
        (38, '38 KG'),
        (45, '45 KG'),
    ])

    # Food specific fields (only used if category is 'food')
    preparation_time = models.IntegerField(help_text='Preparation time in minutes', blank=True, null=True)
    is_vegan = models.BooleanField(default=False)
    is_halal = models.BooleanField(default=False)
    
    # Common fields
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.category.name == 'gas':
            return f"{self.name} - {self.get_gas_type_display()} ({self.get_tank_size_display() if self.tank_size else 'N/A'})"
        return f"{self.name} - {self.category.name}"

    class Meta:
        ordering = ['category', 'name']
        
    @property
    def display_unit(self):
        if self.category.name == 'gas' and self.tank_size:
            return f"{self.tank_size} KG"
        return self.get_unit_display()

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='business_orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_address = models.CharField(max_length=255)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.business.name}"

    class Meta:
        ordering = ['-created_at']

class BusinessProfile(models.Model):
    """Model for storing business profile details"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='categories/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)