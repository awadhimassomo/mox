import os
import django
import sys
from datetime import datetime, timedelta
import random
import string
import uuid

# Set up Django environment
print("Setting up Django environment...")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

print("Django setup complete!")

from django.utils import timezone
from orders.models import Order, OrderItem
from customers.models import CustomerProfile, DeliveryAddress
from business.models import Business, Product
from riders.models import Rider
from operations.models import CustomUser
from customers.models import OrderAssignmentGroup
from orders.models import OrderAssignmentGroup as OrdersAssignmentGroup

def create_test_order():
    print("Creating test order...")
    
    # Get or create a test user
    try:
        user, created = CustomUser.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'testuser@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'is_active': True
            }
        )
        if created:
            user.set_password('testpassword')
            user.save()
            print(f"Created test user: {user.username}")
        else:
            print(f"Using existing test user: {user.username}")
    except Exception as e:
        print(f"Error creating test user: {str(e)}")
        return
    
    # Get or create a customer profile
    try:
        customer, created = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={
                'phone_number': '+255712345678'
            }
        )
        if created:
            print(f"Created customer profile for {user.username}")
        else:
            print(f"Using existing customer profile for {user.username}")
    except Exception as e:
        print(f"Error creating customer profile: {str(e)}")
        return
    
    # Get or create a business
    try:
        business, created = Business.objects.get_or_create(
            name='Test Gas Station',
            defaults={
                'address': 'Test Address, Arusha',
                'phone': '+255787654321',
                'latitude': -3.386182,
                'longitude': 36.668648,
                'region': 'arusha'
            }
        )
        if created:
            print(f"Created business: {business.name}")
        else:
            print(f"Using existing business: {business.name}")
    except Exception as e:
        print(f"Error creating business: {str(e)}")
        return
    
    # Get or create a product
    try:
        product, created = Product.objects.get_or_create(
            name='Test Gas Cylinder',
            business=business,
            defaults={
                'description': 'Test gas cylinder for testing',
                'price': 50000,
                'is_available': True
            }
        )
        if created:
            print(f"Created product: {product.name}")
        else:
            print(f"Using existing product: {product.name}")
    except Exception as e:
        print(f"Error creating product: {str(e)}")
        return
    
    # Get or create a delivery address
    try:
        address, created = DeliveryAddress.objects.get_or_create(
            customer=customer,
            name='Test Address',
            defaults={
                'street': 'Test Street',
                'area': 'Test Area',
                'city': 'Arusha',
                'latitude': -3.372793,
                'longitude': 36.694223,
                'is_default': True
            }
        )
        if created:
            print(f"Created delivery address: {address.name}")
        else:
            print(f"Using existing delivery address: {address.name}")
    except Exception as e:
        print(f"Error creating delivery address: {str(e)}")
        return
    
    # Get or create a rider
    try:
        rider, created = Rider.objects.get_or_create(
            phone_number='+255712999888',
            defaults={
                'first_name': 'Test',
                'last_name': 'Rider',
                'latitude': -3.386182,
                'longitude': 36.668648,
                'is_available': True,
                'region': 'arusha'
            }
        )
        if created:
            print(f"Created rider: {rider.first_name} {rider.last_name}")
        else:
            print(f"Using existing rider: {rider.first_name} {rider.last_name}")
    except Exception as e:
        print(f"Error creating rider: {str(e)}")
        return
    
    # Generate a unique order number
    timestamp = timezone.now().strftime('%y%m%d%H%M')
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    order_number = f"MO{timestamp}{random_chars}"
    
    # Create order
    try:
        order = Order.objects.create(
            order_number=order_number,
            customer=customer,
            customer_name=f"{user.first_name} {user.last_name}",
            business=business,
            delivery_address=address,
            delivery_location=f"{address.street}, {address.area}, {address.city}",
            delivery_latitude=address.latitude,
            delivery_longitude=address.longitude,
            subtotal=50000,
            delivery_fee=2000,
            total=52000,
            payment_method='CASH',
            payment_status='PENDING',
            status='assigned'
        )
        print(f"Created order: {order.order_number}")
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return
    
    # Create order item
    try:
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            unit_price=product.price,
            total_price=product.price
        )
        print(f"Created order item: {order_item}")
    except Exception as e:
        print(f"Error creating order item: {str(e)}")
        return
    
    # Create assignment groups
    try:
        # Create customers app assignment group
        customers_assignment_group = OrderAssignmentGroup.objects.create(
            group_id=uuid.uuid4()
        )
        customers_assignment_group.riders.add(rider)
        print(f"Created customers assignment group")
        
        # Create orders app assignment group
        orders_assignment_group = OrdersAssignmentGroup.objects.create(
            order=order
        )
        orders_assignment_group.riders.add(rider)
        print(f"Created orders assignment group")
    except Exception as e:
        print(f"Error creating assignment groups: {str(e)}")
        return
    
    print("\nTest order created successfully!")
    print(f"Order Number: {order.order_number}")
    print(f"Customer: {order.customer_name}")
    print(f"Business: {order.business.name}")
    print(f"Status: {order.status}")
    print(f"Total: TZS {order.total}")
    print(f"Rider assigned: {rider.first_name} {rider.last_name}")

if __name__ == '__main__':
    create_test_order()
