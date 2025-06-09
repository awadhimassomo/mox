"""
Script to diagnose and fix business categories issue
"""
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

# Import models after Django setup
from business.models import Business, Category
from operations.models import CustomUser

# User ID to check (change if needed)
USER_ID = 104

def main():
    print("=" * 50)
    print("BUSINESS CATEGORIES DIAGNOSTIC")
    print("=" * 50)
    
    # Check user
    try:
        user = CustomUser.objects.get(id=USER_ID)
        print(f"[OK] User found: {user.username} (ID: {USER_ID})")
    except CustomUser.DoesNotExist:
        print(f"[ERROR] ERROR: User with ID {USER_ID} not found!")
        return
    
    # Check business
    businesses = Business.objects.filter(user=user)
    if not businesses.exists():
        print(f"[ERROR] ERROR: No business found for user {user.username}!")
        
        # Create business?
        choice = input("Would you like to create a business for this user? (y/n): ")
        if choice.lower() == 'y':
            name = input("Enter business name: ")
            business = Business.objects.create(
                user=user,
                name=name,
                is_active=True
            )
            print(f"[OK] Created business: {business.name} (ID: {business.id})")
        else:
            return
    else:
        business = businesses.first()
        print(f"[OK] Business found: {business.name} (ID: {business.id})")
    
    # Check categories
    categories = Category.objects.filter(business=business)
    print(f"Found {categories.count()} categories for business '{business.name}'")
    
    if categories.exists():
        print("\nCATEGORIES:")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat.name} (ID: {cat.id})")
    else:
        print("\n[ERROR] No categories found for this business!")
        
        # Create sample categories?
        choice = input("Would you like to create sample categories? (y/n): ")
        if choice.lower() == 'y':
            sample_categories = [
                "Food", "Electronics", "Clothing", "Furniture", 
                "Health & Beauty", "Gas"
            ]
            
            print("\nCreating sample categories...")
            for cat_name in sample_categories:
                slug = cat_name.lower().replace(' & ', '-').replace(' ', '-')
                category = Category.objects.create(
                    name=cat_name,
                    slug=slug,
                    business=business,
                    is_active=True,
                    is_top_level=True,
                    category_type=cat_name.lower() if cat_name.lower() in ['food', 'electronics', 'clothing', 'furniture', 'gas'] else 'general'
                )
                print(f"  [CREATED] Created category: {category.name} (ID: {category.id})")
            
            # Recheck count
            categories = Category.objects.filter(business=business)
            print(f"\n[OK] Total categories now: {categories.count()}")
    
    print("\n" + "=" * 50)
    print("DIAGNOSIS COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()
