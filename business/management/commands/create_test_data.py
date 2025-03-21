import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from business.models import Business, Product, Category, REGION_CHOICES
from django.db.models import Q

class Command(BaseCommand):
    help = 'Creates test data for products for each business'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write("Starting test data creation...")
            
            # Get all businesses
            businesses = Business.objects.all()
            
            if not businesses.exists():
                self.stdout.write(self.style.WARNING('No businesses found. Please create businesses first.'))
                return
            
            self.stdout.write(f'Found {businesses.count()} businesses')
            
            # Get or create Gas category
            gas_category, created = Category.objects.get_or_create(
                name='Gas',
                defaults={
                    'description': 'Gas tanks for cooking and heating',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'Created Gas category')
            
            # Create one test product for each business
            for business in businesses:
                self.stdout.write(f'Creating product for business: {business.name}')
                
                # Create a simple product
                product = Product.objects.create(
                    business=business,
                    category=gas_category,
                    name=f"LPG Tank - 13kg for {business.name}",
                    description="13kg LPG gas tank for cooking and heating",
                    price=50000,
                    stock_quantity=10,
                    unit='kg',
                    gas_type='lpg',
                    tank_size=13,
                    is_available=True
                )
                
                self.stdout.write(f'Created product: {product.name}')
            
            self.stdout.write(self.style.SUCCESS('Successfully created test products'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
