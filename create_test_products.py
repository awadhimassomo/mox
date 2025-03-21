import os
import django
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

from business.models import Business, Product, Category
from django.db.models import Q

def create_categories():
    """Create various product categories"""
    categories = [
        {'name': 'Gas', 'description': 'Gas tanks for cooking and heating'},
        {'name': 'Food', 'description': 'Food products including groceries and ingredients'},
        {'name': 'Electronics', 'description': 'Electronic devices and accessories'},
        {'name': 'Flowers', 'description': 'Fresh flowers and floral arrangements'},
        {'name': 'Household', 'description': 'Household items and home essentials'},
        {'name': 'Beverages', 'description': 'Drinks including water, soda, and juice'},
        {'name': 'Stationery', 'description': 'Office and school supplies'},
        {'name': 'Clothing', 'description': 'Apparel and fashion items'}
    ]
    
    created_categories = []
    for cat_data in categories:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'is_active': True
            }
        )
        created_categories.append(category)
        print(f"{'Created' if created else 'Found'} category: {category.name}")
    
    return created_categories

def create_gas_products(business, gas_category):
    """Create gas products for a business"""
    # Gas tank sizes in kg
    tank_sizes = [6, 13, 15, 38, 45]
    
    # Gas types
    gas_types = [
        ('lpg', 'LPG'), 
        ('natural', 'Natural Gas'), 
        ('propane', 'Propane'), 
        ('butane', 'Butane')
    ]
    
    products_created = 0
    
    # Create 3-5 gas products
    num_products = random.randint(3, 5)
    for _ in range(num_products):
        tank_size = random.choice(tank_sizes)
        gas_type = random.choice(gas_types)
        
        # Create a product name
        product_name = f"{gas_type[1]} Tank - {tank_size}kg"
        
        # Check if product already exists for this business
        existing_product = Product.objects.filter(
            Q(business=business) & 
            Q(name__icontains=product_name)
        ).first()
        
        if not existing_product:
            # Create price (between 5000 and 100000 TZS)
            price = random.randint(5000, 100000)
            
            # Create stock (between 5 and 50)
            stock = random.randint(5, 50)
            
            product = Product.objects.create(
                business=business,
                category=gas_category,
                name=product_name,
                description=f"{tank_size}kg {gas_type[1]} gas tank for cooking and heating",
                price=price,
                stock_quantity=stock,
                unit='kg',
                gas_type=gas_type[0],
                tank_size=tank_size,
                is_available=True
            )
            
            products_created += 1
            print(f"Created gas product: {product.name} for {business.name}")
    
    return products_created

def create_food_products(business, food_category):
    """Create food products for a business"""
    food_items = [
        "Rice (1kg)", "Maize Flour (2kg)", "Wheat Flour (1kg)", 
        "Sugar (1kg)", "Salt (500g)", "Cooking Oil (1L)",
        "Beans (1kg)", "Lentils (500g)", "Pasta (500g)",
        "Bread", "Eggs (Tray of 30)", "Milk (1L)"
    ]
    
    products_created = 0
    
    # Create 4-8 food products
    num_products = random.randint(4, 8)
    for _ in range(num_products):
        food_item = random.choice(food_items)
        
        # Check if product already exists for this business
        existing_product = Product.objects.filter(
            Q(business=business) & 
            Q(name__icontains=food_item)
        ).first()
        
        if not existing_product:
            # Create price (between 1000 and 20000 TZS)
            price = random.randint(1000, 20000)
            
            # Create stock (between 10 and 100)
            stock = random.randint(10, 100)
            
            product = Product.objects.create(
                business=business,
                category=food_category,
                name=food_item,
                description=f"Fresh {food_item} available for delivery",
                price=price,
                stock_quantity=stock,
                unit='item',
                is_available=True
            )
            
            products_created += 1
            print(f"Created food product: {product.name} for {business.name}")
    
    return products_created

def create_electronics_products(business, electronics_category):
    """Create electronics products for a business"""
    electronics_items = [
        "Smartphone Charger", "USB Cable", "Earphones", 
        "Power Bank", "Memory Card (32GB)", "Flash Drive (16GB)",
        "Bluetooth Speaker", "Phone Case", "Screen Protector",
        "Laptop Cooling Pad", "Wireless Mouse", "Keyboard"
    ]
    
    products_created = 0
    
    # Create 3-6 electronics products
    num_products = random.randint(3, 6)
    for _ in range(num_products):
        electronics_item = random.choice(electronics_items)
        
        # Check if product already exists for this business
        existing_product = Product.objects.filter(
            Q(business=business) & 
            Q(name__icontains=electronics_item)
        ).first()
        
        if not existing_product:
            # Create price (between 5000 and 50000 TZS)
            price = random.randint(5000, 50000)
            
            # Create stock (between 5 and 30)
            stock = random.randint(5, 30)
            
            product = Product.objects.create(
                business=business,
                category=electronics_category,
                name=electronics_item,
                description=f"Quality {electronics_item} for your devices",
                price=price,
                stock_quantity=stock,
                unit='item',
                is_available=True
            )
            
            products_created += 1
            print(f"Created electronics product: {product.name} for {business.name}")
    
    return products_created

def create_flower_products(business, flower_category):
    """Create flower products for a business"""
    flower_items = [
        "Rose Bouquet", "Lily Arrangement", "Tulip Bunch", 
        "Sunflower Bouquet", "Mixed Flower Basket", "Orchid Plant",
        "Wedding Flowers", "Birthday Bouquet", "Anniversary Flowers",
        "Condolence Wreath", "Single Rose", "Potted Plant"
    ]
    
    products_created = 0
    
    # Create 3-5 flower products
    num_products = random.randint(3, 5)
    for _ in range(num_products):
        flower_item = random.choice(flower_items)
        
        # Check if product already exists for this business
        existing_product = Product.objects.filter(
            Q(business=business) & 
            Q(name__icontains=flower_item)
        ).first()
        
        if not existing_product:
            # Create price (between 10000 and 80000 TZS)
            price = random.randint(10000, 80000)
            
            # Create stock (between 3 and 20)
            stock = random.randint(3, 20)
            
            product = Product.objects.create(
                business=business,
                category=flower_category,
                name=flower_item,
                description=f"Beautiful {flower_item} for all occasions",
                price=price,
                stock_quantity=stock,
                unit='item',
                is_available=True
            )
            
            products_created += 1
            print(f"Created flower product: {product.name} for {business.name}")
    
    return products_created

def main():
    """Main function to create test products"""
    print("Starting test product creation...")
    
    # Create categories
    categories = create_categories()
    
    # Get category objects
    gas_category = next((c for c in categories if c.name == 'Gas'), None)
    food_category = next((c for c in categories if c.name == 'Food'), None)
    electronics_category = next((c for c in categories if c.name == 'Electronics'), None)
    flower_category = next((c for c in categories if c.name == 'Flowers'), None)
    
    # Get all businesses
    businesses = Business.objects.all()
    
    if not businesses.exists():
        print("No businesses found. Please create businesses first.")
        return
    
    print(f"Found {businesses.count()} businesses")
    
    total_products_created = 0
    
    # For each business, create products from different categories
    for business in businesses:
        print(f"\nCreating products for business: {business.name}")
        
        # Assign 1-3 random categories to each business
        num_categories = random.randint(1, 3)
        business_categories = random.sample(categories, num_categories)
        
        # Always include gas category
        if gas_category and gas_category not in business_categories:
            business_categories.append(gas_category)
        
        # Create products for each category
        for category in business_categories:
            if category.name == 'Gas':
                total_products_created += create_gas_products(business, category)
            elif category.name == 'Food':
                total_products_created += create_food_products(business, category)
            elif category.name == 'Electronics':
                total_products_created += create_electronics_products(business, category)
            elif category.name == 'Flowers':
                total_products_created += create_flower_products(business, category)
    
    print(f"\nSuccessfully created {total_products_created} products across {businesses.count()} businesses")

if __name__ == "__main__":
    main()
