from django.core.management.base import BaseCommand
from orders.models import TransportMode
from decimal import Decimal

class Command(BaseCommand):
    help = 'Creates sample transport modes for testing'

    def handle(self, *args, **options):
        transport_modes = [
            {
                'name': 'Motorcycle',
                'description': 'Fast delivery with a motorcycle for small packages',
                'base_price': Decimal('1500.00'),
                'price_per_km': Decimal('200.00'),
                'max_distance': 15,
                'max_weight': Decimal('10.00'),
                'is_active': True
            },
            {
                'name': 'Bicycle',
                'description': 'Eco-friendly delivery for light packages in nearby areas',
                'base_price': Decimal('1000.00'),
                'price_per_km': Decimal('150.00'),
                'max_distance': 5,
                'max_weight': Decimal('5.00'),
                'is_active': True
            },
            {
                'name': 'Pickup Truck',
                'description': 'Delivery for large or heavy items',
                'base_price': Decimal('3000.00'),
                'price_per_km': Decimal('350.00'),
                'max_distance': 30,
                'max_weight': Decimal('200.00'),
                'is_active': True
            },
        ]

        created_count = 0
        for mode_data in transport_modes:
            _, created = TransportMode.objects.get_or_create(
                name=mode_data['name'],
                defaults=mode_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created transport mode: {mode_data["name"]}'))
            else:
                self.stdout.write(f'Transport mode already exists: {mode_data["name"]}')

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} transport modes'))
