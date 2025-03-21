import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

from business.models import Category

# Define categories to create
categories = [
    {
        'name': 'Gas',
        'description': 'Gas tanks and related products for cooking and heating',
        'is_active': True
    },
    {
        'name': 'Food',
        'description': 'Food products including groceries, prepared meals, and ingredients',
        'is_active': True
    },
    {
        'name': 'Electronics',
        'description': 'Electronic devices, gadgets, and accessories',
        'is_active': True
    },
    {
        'name': 'Flowers',
        'description': 'Fresh flowers, bouquets, and floral arrangements',
        'is_active': True
    },
    {
        'name': 'Household',
        'description': 'Household items, cleaning supplies, and home essentials',
        'is_active': True
    },
    {
        'name': 'Beverages',
        'description': 'Drinks including water, soda, juice, and alcoholic beverages',
        'is_active': True
    },
    {
        'name': 'Stationery',
        'description': 'Office and school supplies',
        'is_active': True
    },
    {
        'name': 'Clothing',
        'description': 'Apparel and fashion items',
        'is_active': True
    }
]

def populate_categories():
    print("Creating categories...")
    for category_data in categories:
        category, created = Category.objects.get_or_create(
            name=category_data['name'],
            defaults={
                'description': category_data['description'],
                'is_active': category_data['is_active']
            }
        )
        if created:
            print(f"Created category: {category.name}")
        else:
            print(f"Category already exists: {category.name}")
    
    print("Categories created successfully!")

if __name__ == '__main__':
    populate_categories()
