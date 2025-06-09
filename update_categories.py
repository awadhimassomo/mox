"""
Script to update existing categories to associate them with a business.
This is a one-time script to be run after adding the business field to Category model.
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

# Import models
from business.models import Category, Business
from django.contrib.auth import get_user_model

User = get_user_model()

def assign_categories_to_business():
    """Assign all existing categories to the first available business"""
    
    # Check if there are categories without business
    orphan_categories = Category.objects.filter(business__isnull=True)
    orphan_count = orphan_categories.count()
    
    if orphan_count == 0:
        print("No orphan categories found. All categories already have a business assigned.")
        return
    
    # Get all businesses
    businesses = Business.objects.all()
    
    if not businesses.exists():
        print("No businesses found in the database. Please create at least one business before running this script.")
        return
    
    # Get the first business as default owner
    default_business = businesses.first()
    print(f"Using business '{default_business.name}' as default owner for orphan categories.")
    
    # Update all orphan categories
    orphan_categories.update(business=default_business)
    print(f"Successfully assigned {orphan_count} categories to business '{default_business.name}'.")

if __name__ == "__main__":
    assign_categories_to_business()
    print("Category update complete.")
