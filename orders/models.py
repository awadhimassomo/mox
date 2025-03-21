from django.utils import timezone
import uuid
from django.db import models
from customers.models import CustomerProfile, DeliveryAddress
from riders.models import Rider
from business.models import Business, Product



class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('processing', 'Processing'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('in_transit', 'In-Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash on Delivery'),
        ('mpesa', 'M-Pesa'),
        ('tigopesa', 'Tigo Pesa'),
        ('airtelmoney', 'Airtel Money')
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ]

     # Tracking and Identification
    order_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    uuid_tracking = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # Customer Information
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)  # Add this
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='orders', null=True)  # Add this
    delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.SET_NULL, null=True, blank=True)  # Add this

    # Customer Information
    customer_name = models.CharField(max_length=100, null=True)  # For both registered and guest customers

    # Business (Pickup Location)
    pickup_location = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='pickup_orders', null=True, blank=True)
    
    # Pickup Coordinates (Auto-assigned from Business)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Delivery Information
    delivery_location = models.CharField(max_length=255, null=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Status and Assignment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rider = models.ForeignKey(Rider, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Payment Information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=100, blank=True)

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=1000)
    surge_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bulk_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Additional Information
    notes = models.TextField(blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def save(self, *args, **kwargs):
        """Automatically assigns pickup latitude and longitude from Business when saving"""

        # Always save status in lowercase to prevent case inconsistency
        if self.status:
            self.status = self.status.lower()
        
        # Generate order number if not set
        if not self.order_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.order_number = f"MO{timestamp}"

        # Ensure pickup_location is a Business instance before fetching coordinates
        if self.pickup_location and isinstance(self.pickup_location, Business):
            self.pickup_latitude = self.pickup_location.latitude
            self.pickup_longitude = self.pickup_location.longitude
        else:
            self.pickup_latitude = None
            self.pickup_longitude = None

        # Ensure subtotal is not None before calculations
        if self.subtotal is None:
            self.subtotal = 0.0

        # Calculate surge fee during peak hours
        if self.is_peak_hour():
            self.surge_fee = float(self.subtotal) * 0.10  # 10% surge during peak hours

        # Calculate bulk discount if applicable
        # Only try to access items if the order has been saved (has a primary key)
        if self.pk and hasattr(self, 'items'):
            total_quantity = sum(item.quantity for item in self.items.all())
            if total_quantity > 1:
                discount_rate = self.calculate_bulk_discount(total_quantity)
                self.bulk_discount = float(self.subtotal) * discount_rate

        # Calculate final total
        self.total = float(self.subtotal) + float(self.delivery_fee) + float(self.surge_fee) - float(self.bulk_discount)

        super().save(*args, **kwargs)  # Save the order

    def __str__(self):
        return f"Order #{self.order_number} - {self.customer_name}"

    def is_peak_hour(self):
        """Check if current time is during peak hours"""
        current_hour = timezone.now().hour
        return (7 <= current_hour < 9) or (17 <= current_hour < 19)

    def calculate_bulk_discount(self, quantity):
        """Calculate bulk discount based on order quantity"""
        if quantity >= 10:
            return 0.15  # 15% discount
        elif quantity >= 5:
            return 0.10  # 10% discount
        elif quantity >= 3:
            return 0.05  # 5% discount
        return 0

    def get_display_id(self):
        """Return the order number if it exists, otherwise fall back to ID"""
        return self.order_number if self.order_number else f"{self.id}"

    def assign_rider(self, rider):
        """Assign a rider to this order"""
        self.rider = rider
        self.status = 'assigned'
        self.save()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items',null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} - Order #{self.order.order_number}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
class OrderAssignmentGroup(models.Model):
    """
    Model to track groups of riders assigned to an order.
    Used for managing order assignments and tracking which riders have been offered an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='assignment_groups')
    riders = models.ManyToManyField('riders.Rider', related_name='assignment_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    group_id = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return f"Assignment Group {self.group_id} for Order {self.order.get_display_id()}"

    class Meta:
        ordering = ['-created_at']

class OrderRiderAction(models.Model):
    ACTION_CHOICES = [
        ('assigned', 'Assigned'),
        ('viewed', 'Viewed'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('preparing', 'Preparing'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('started', 'Started Delivery'),
        ('arrived_pickup', 'Arrived at Pickup'),
        ('collected', 'Collected Gas Tanks'),
        ('in_transit', 'In Transit'),
        ('arrived_delivery', 'Arrived at Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='rider_actions')
    rider = models.ForeignKey('riders.Rider', on_delete=models.CASCADE, related_name='order_actions')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['order', 'rider', 'action_type']),
            models.Index(fields=['rider', 'action_type']),
            models.Index(fields=['order', 'action_type']),
        ]
    
    def __str__(self):
        return f"{self.rider} {self.get_action_type_display()} order {self.order.order_number}"

    @classmethod
    def record_action(cls, order, rider, action_type, notes="", lat=None, lng=None):
        """Helper method to easily record rider actions"""
        action = cls(
            order=order,
            rider=rider,
            action_type=action_type,
            notes=notes,
            location_lat=lat,
            location_lng=lng
        )
        action.save()
        
        # Update the order model based on action type
        if action_type == 'accepted':
            order.accepted_by = rider
            order.accepted_at = timezone.now()
            if order.status == 'assigned':
                order.status = 'preparing'
            order.save()
        elif action_type == 'declined':
            order.declined_by.add(rider)
            order.save()
        elif action_type == 'completed':
            order.completed_by = rider
            order.completed_at = timezone.now()
            order.status = 'delivered'
            order.save()
        
        return action
        
    @classmethod
    def get_rider_order_stats(cls, rider_id=None, order_id=None, action_types=None, start_date=None, end_date=None):
        """
        Get statistics about rider actions on orders.
        
        Args:
            rider_id: Optional rider ID to filter by
            order_id: Optional order ID to filter by
            action_types: List of action types to include
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary with stats about rider actions
        """
        queryset = cls.objects.all()
        
        # Apply filters
        if rider_id:
            queryset = queryset.filter(rider_id=rider_id)
        
        if order_id:
            queryset = queryset.filter(order_id=order_id)
            
        if action_types:
            queryset = queryset.filter(action_type__in=action_types)
            
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
            
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # Calculate stats
        stats = {
            'total_actions': queryset.count(),
            'actions_by_type': {}
        }
        
        # Count by action type
        for action_type, _ in cls.ACTION_CHOICES:
            count = queryset.filter(action_type=action_type).count()
            stats['actions_by_type'][action_type] = count
            
        return stats