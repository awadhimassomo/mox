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
    phone = '255787654321'
    try:
        print('Creating user...')
        user = User.objects.create_user(
            username=phone,
            email='test2@example.com',
            password='test123',
            is_staff=True
        )
        print('User created successfully')
        
        print('Creating profile...')
        UserProfile.objects.create(
            user=user,
            phone=phone,
            region='dar_es_salaam'
        )
        print('Profile created successfully')
        
    except Exception as e:
        print('Error:', str(e))
        print('Traceback:', traceback.format_exc())

if __name__ == '__main__':
    create_test_user()
