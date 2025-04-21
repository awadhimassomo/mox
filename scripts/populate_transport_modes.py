import os
import sys
import django
from decimal import Decimal

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_exp_core.settings')
django.setup()

from orders.models import TransportMode

def populate_transport_modes():
    """
    Populate the database with the four transport modes:
    1. Boda - Motorcycle
    2. Guta - Three-wheeler (like a tuk-tuk)
    3. Kirikuu - Small pickup truck
    4. Kenta - Larger delivery van
    """
    
    # Transport mode specifications
    transport_modes = [
        {
            'name': 'Boda',
            'description': 'Motorcycle delivery - Fast and economical for small packages and short distances.',
            'base_price': Decimal('1500.00'),
            'price_per_km': Decimal('300.00'),
            'max_distance': 10,
            'max_weight': Decimal('15.00')
        },
        {
            'name': 'Guta',
            'description': 'Three-wheeler vehicle - Good balance of cost and capacity for medium-sized packages.',
            'base_price': Decimal('2500.00'),
            'price_per_km': Decimal('500.00'),
            'max_distance': 15,
            'max_weight': Decimal('50.00')
        },
        {
            'name': 'Kirikuu',
            'description': 'Small pickup truck - For larger deliveries and multiple gas cylinders.',
            'base_price': Decimal('3500.00'),
            'price_per_km': Decimal('700.00'),
            'max_distance': 25,
            'max_weight': Decimal('150.00')
        },
        {
            'name': 'Kenta',
            'description': 'Delivery van - For bulk orders and commercial deliveries.',
            'base_price': Decimal('5000.00'),
            'price_per_km': Decimal('1000.00'),
            'max_distance': 40,
            'max_weight': Decimal('300.00')
        }
    ]
    
    # For each transport mode, create or update
    for mode_data in transport_modes:
        transport_mode, created = TransportMode.objects.update_or_create(
            name=mode_data['name'],
            defaults={
                'description': mode_data['description'],
                'base_price': mode_data['base_price'],
                'price_per_km': mode_data['price_per_km'],
                'max_distance': mode_data['max_distance'],
                'max_weight': mode_data['max_weight'],
                'is_active': True
            }
        )
        
        if created:
            print(f"Created new transport mode: {transport_mode.name}")
        else:
            print(f"Updated transport mode: {transport_mode.name}")
    
    print("Transport modes populated successfully!")

if __name__ == "__main__":
    populate_transport_modes()
