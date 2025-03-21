import os
import django
import sys
from datetime import datetime, timedelta
import math

# Set up Django environment
print("Setting up Django environment...")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

print("Django setup complete!")

from orders.models import Order
from customers.models import Customer
from business.models import Business
from riders.models import Rider

# Rider data (your location in Sombetini)
test_rider_data = {
    'first_name': 'Mean',
    'last_name': 'Rider',
    'phone_number': '+255712999888',
    'latitude': -3.386182,
    'longitude': 36.668648,
    'is_available': True,
    'region': 'arusha'
}

# Test data for multiple scenarios
test_scenarios = [
    {
        'name': 'Nearby Order - Njiro',
        'business_data': {
            'name': 'Sombetini Gas Point',
            'address': 'Near Sombetini Primary School, Arusha',
            'latitude': -3.385982,  # ~200m from rider
            'longitude': 36.668748,
            'phone': '+255789123999',
            'gas_types_available': ['6KG LPG', '13KG LPG', '15KG LPG']
        },
        'order_data': {
            'customer_phone': '+255745678999',
            'delivery_address': 'Njiro Complex, Near Shoppers Plaza, Arusha',
            'delivery_latitude': -3.372793,
            'delivery_longitude': 36.694223,
            'quantity': 1,
            'region': 'arusha'
        }
    },
    {
        'name': 'Far Order - USA River',
        'business_data': {
            'name': 'USA River Gas',
            'address': 'USA River Main Road, Near Bus Stand',
            'latitude': -3.361944,  # ~25km from rider
            'longitude': 36.849167,
            'phone': '+255789123888',
            'gas_types_available': ['6KG LPG', '13KG LPG']
        },
        'order_data': {
            'customer_phone': '+255745678888',
            'delivery_address': 'USA River, Near Africafe',
            'delivery_latitude': -3.362944,
            'delivery_longitude': 36.847167,
            'quantity': 2,
            'region': 'arusha'
        }
    },
    {
        'name': 'Different Region - Dar',
        'business_data': {
            'name': 'Kariakoo Gas',
            'address': 'Kariakoo Market, Dar es Salaam',
            'latitude': -6.818056,  # In Dar es Salaam
            'longitude': 39.273889,
            'phone': '+255789123777',
            'gas_types_available': ['6KG LPG', '13KG LPG', '15KG LPG']
        },
        'order_data': {
            'customer_phone': '+255745678777',
            'delivery_address': 'Masaki, Near Slipway',
            'delivery_latitude': -6.745833,
            'delivery_longitude': 39.290278,
            'quantity': 1,
            'region': 'dar_es_salaam'
        }
    },
    {
        'name': 'Nearby Order - Kijenge',
        'business_data': {
            'name': 'Kijenge Gas Point',
            'address': 'Kijenge Shopping Center, Arusha',
            'latitude': -3.384167,  # ~500m from rider
            'longitude': 36.672222,
            'phone': '+255789123666',
            'gas_types_available': ['13KG LPG']
        },
        'order_data': {
            'customer_phone': '+255745678666',
            'delivery_address': 'Kijenge, Near Green Hut',
            'delivery_latitude': -3.383167,
            'delivery_longitude': 36.673222,
            'quantity': 3,
            'region': 'arusha'
        }
    }
]

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth's radius in meters
    
    # Convert to float in case we get Decimal objects
    lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2) * math.sin(delta_phi/2) + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda/2) * math.sin(delta_lambda/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

def create_test_scenario():
    print("Creating test scenarios...")
    
    # Create rider (you) first
    try:
        rider, created = Rider.objects.get_or_create(
            phone_number=test_rider_data['phone_number'],
            defaults={
                'first_name': test_rider_data['first_name'],
                'last_name': test_rider_data['last_name'],
                'latitude': test_rider_data['latitude'],
                'longitude': test_rider_data['longitude'],
                'is_available': test_rider_data['is_available'],
                'region': test_rider_data['region']
            }
        )
        if created:
            print(f"Created rider: {test_rider_data['first_name']} {test_rider_data['last_name']}")
        else:
            print(f"Rider already exists: {test_rider_data['first_name']} {test_rider_data['last_name']}")
            # Update rider location
            rider.latitude = test_rider_data['latitude']
            rider.longitude = test_rider_data['longitude']
            rider.save()
            print(f"Updated rider location")
    except Exception as e:
        print(f"Error creating rider: {str(e)}")
        return
    
    for scenario in test_scenarios:
        print(f"\nProcessing {scenario['name']}...")
        
        # Create business
        try:
            business, created = Business.objects.get_or_create(
                phone=scenario['business_data']['phone'],
                defaults={
                    'name': scenario['business_data']['name'],
                    'address': scenario['business_data']['address'],
                    'latitude': scenario['business_data']['latitude'],
                    'longitude': scenario['business_data']['longitude'],
                    'region': scenario['order_data']['region']  # Use same region as order
                }
            )
            if created:
                print(f"Created business: {business.name}")
            else:
                # Update business location if it exists
                business.latitude = scenario['business_data']['latitude']
                business.longitude = scenario['business_data']['longitude']
                business.save()
                print(f"Business already exists: {business.name}")
                print(f"Updated business location")

        except Exception as e:
            print(f"Error creating business: {str(e)}")
            continue

        # Create customer
        try:
            customer, created = Customer.objects.get_or_create(
                phone=scenario['order_data']['customer_phone'],
                defaults={
                    'region': scenario['order_data']['region']
                }
            )
        except Exception as e:
            print(f"Error creating customer: {str(e)}")
            continue
        
        # Calculate distances
        rider_to_business = calculate_distance(
            rider.latitude, rider.longitude,
            business.latitude, business.longitude
        )
        
        business_to_customer = calculate_distance(
            business.latitude, business.longitude,
            scenario['order_data']['delivery_latitude'],
            scenario['order_data']['delivery_longitude']
        )
        
        # Create order
        try:
            order = Order.objects.create(
                customer_name=f"Customer {scenario['order_data']['customer_phone']}",
                business=business,
                delivery_location=scenario['order_data']['delivery_address'],
                delivery_latitude=scenario['order_data']['delivery_latitude'],
                delivery_longitude=scenario['order_data']['delivery_longitude'],
                quantity=scenario['order_data']['quantity'],
                status='pending',
                created_at=datetime.now()
            )
            
            print(f"""
Order Details:
-------------
Tracking Number: {order.tracking_number}
Business: {business.name}
- Location: {scenario['business_data']['address']}
- Distance from you: {rider_to_business:.0f}m
- Status: {'Within range (300m)' if rider_to_business <= 300 else 'Out of range'}

Customer Phone: {customer.phone}
- Region: {scenario['order_data']['region']}
- Delivery Location: {scenario['order_data']['delivery_address']}
- Distance from business: {business_to_customer/1000:.1f}km
- Quantity: {scenario['order_data']['quantity']}

Order Status: {order.status.upper()}
""")
                
        except Exception as e:
            print(f"Error creating order: {str(e)}")

if __name__ == '__main__':
    create_test_scenario()
