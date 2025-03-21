from django.core.management.base import BaseCommand
from business.models import Business

class Command(BaseCommand):
    help = 'Lists all businesses in the database'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write("Listing all businesses...")
            businesses = Business.objects.all()
            
            if not businesses.exists():
                self.stdout.write(self.style.WARNING('No businesses found in the database.'))
                return
            
            self.stdout.write(f'Found {businesses.count()} businesses:')
            
            for business in businesses:
                self.stdout.write(f'- {business.name} (ID: {business.id})')
                
            self.stdout.write(self.style.SUCCESS('Successfully listed all businesses'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
