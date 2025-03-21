import os
import django
import traceback

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

# Import models
from django.contrib.auth import get_user_model
from operations.models import UserProfile

User = get_user_model()

def create_test_user():
    phone = '255789012345'  # Different phone number
    try:
        # First check if user exists
        if User.objects.filter(username=phone).exists():
            print(f'User with phone {phone} already exists')
            return
            
        if UserProfile.objects.filter(phone=phone).exists():
            print(f'Profile with phone {phone} already exists')
            return
        
        print('Creating user...')
        user = User.objects.create_user(
            username=phone,
            email='test3@example.com',
            password='test123',
            is_staff=True
        )
        print(f'User created successfully: {user.username}')
        
        print('Creating profile...')
        profile = UserProfile.objects.create(
            user=user,
            phone=phone,
            region='dar_es_salaam'
        )
        print(f'Profile created successfully: {profile.phone}')
        
    except Exception as e:
        print('Error:', str(e))
        print('Traceback:', traceback.format_exc())
        
        # Cleanup on error
        if 'user' in locals():
            try:
                user.delete()
                print('Cleaned up user due to error')
            except:
                pass

if __name__ == '__main__':
    create_test_user()
