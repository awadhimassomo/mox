"""
Script to test the categories API endpoint response format
"""
import os
import django
import json
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

# Import DRF testing tools
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from business.models import Business, Category

# User ID to test with
USER_ID = 104

def main():
    print("=" * 50)
    print("TESTING CATEGORIES API RESPONSE")
    print("=" * 50)
    
    # Get the user
    User = get_user_model()
    try:
        user = User.objects.get(id=USER_ID)
        print(f"Found user ID {USER_ID}")
    except User.DoesNotExist:
        print(f"Error: User {USER_ID} not found!")
        return
        
    # Set up test client
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Test unauthenticated response first
    print("\nTesting without authentication:")
    client.logout()
    response = client.get('/business/categories/')
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        data = response.data
        print(f"Response contains {len(data)} items")
        if len(data) > 0:
            print("First item sample:")
            print(json.dumps(data[0], indent=2))
        else:
            print("Response is empty list: []")
    else:
        print(f"Response: {response.content.decode()[:200]}")
        
    # Test authenticated response
    print("\nTesting with authentication as user ID {USER_ID}:")
    client.force_authenticate(user=user)
    response = client.get('/business/categories/')
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        data = response.data
        print(f"Response contains {len(data)} items")
        if len(data) > 0:
            print("First item sample:")
            print(json.dumps(data[0], indent=2))
        else:
            print("Response is empty list: []")
    else:
        print(f"Response: {response.content.decode()[:200]}")
    
    # Get user's business and associated categories directly from DB
    print("\nDirect database query results:")
    businesses = Business.objects.filter(user=user)
    if businesses.exists():
        business = businesses.first()
        print(f"Found business: {business.name} (ID: {business.id})")
        
        # Get categories for this business
        categories = Category.objects.filter(business=business)
        print(f"Business has {categories.count()} categories:")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat.name} (ID: {cat.id})")
            # Check specific fields that might be causing issues
            print(f"     - slug: {cat.slug}")
            print(f"     - category_type: {cat.category_type}")
            print(f"     - parent: {cat.parent_id if cat.parent else 'None'}")
    else:
        print("No business found for this user")
        
    print("\n" + "=" * 50)
        
if __name__ == "__main__":
    main()
