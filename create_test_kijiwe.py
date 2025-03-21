import os
import django
import sys

# Set up Django environment
print("Setting up Django environment...")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mo_express.settings')
django.setup()

print("Django setup complete!")

from operations.models import Kijiwe

# Test data for kijiwe locations in Tanzania
test_kijiwe_data = [
    {
        'name': 'Kariakoo Gas Hub',
        'address': 'Kariakoo Market Area, Dar es Salaam',
        'latitude': -6.8235,
        'longitude': 39.2695,
        'region': 'dar_es_salaam'
    },
    {
        'name': 'Ubungo Terminal',
        'address': 'Ubungo Bus Terminal, Dar es Salaam',
        'latitude': -6.7924,
        'longitude': 39.2317,
        'region': 'dar_es_salaam'
    },
    {
        'name': 'Tegeta Gas Point',
        'address': 'Tegeta Nyuki, Dar es Salaam',
        'latitude': -6.7066,
        'longitude': 39.2237,
        'region': 'dar_es_salaam'
    },
    {
        'name': 'Kimara Gas Station',
        'address': 'Kimara Mwisho, Dar es Salaam',
        'latitude': -6.7789,
        'longitude': 39.1875,
        'region': 'dar_es_salaam'
    },
    {
        'name': 'Mbezi Beach Gas Center',
        'address': 'Mbezi Beach, Dar es Salaam',
        'latitude': -6.7242,
        'longitude': 39.2173,
        'region': 'dar_es_salaam'
    },
    {
        'name': 'Arusha Central',
        'address': 'Central Market Area, Arusha',
        'latitude': -3.3667,
        'longitude': 36.6833,
        'region': 'arusha'
    },
    {
        'name': 'Mwanza Gas Point',
        'address': 'Rock City Mall Area, Mwanza',
        'latitude': -2.5167,
        'longitude': 32.9000,
        'region': 'mwanza'
    },
    {
        'name': 'Dodoma Central',
        'address': 'Majengo Area, Dodoma',
        'latitude': -6.1731,
        'longitude': 35.7419,
        'region': 'dodoma'
    },
    {
        'name': 'Tanga Gas Hub',
        'address': 'Central Market, Tanga',
        'latitude': -5.0667,
        'longitude': 39.1000,
        'region': 'tanga'
    },
    {
        'name': 'Morogoro Station',
        'address': 'Msamvu Area, Morogoro',
        'latitude': -6.8235,
        'longitude': 37.6667,
        'region': 'morogoro'
    }
]

def create_test_kijiwe():
    print("Creating test kijiwe locations...")
    
    for kijiwe_data in test_kijiwe_data:
        try:
            print(f"Creating kijiwe: {kijiwe_data['name']}")
            kijiwe, created = Kijiwe.objects.get_or_create(
                name=kijiwe_data['name'],
                defaults={
                    'address': kijiwe_data['address'],
                    'latitude': kijiwe_data['latitude'],
                    'longitude': kijiwe_data['longitude'],
                    'region': kijiwe_data['region']
                }
            )
            if created:
                print(f"Created kijiwe: {kijiwe.name}")
            else:
                print(f"Kijiwe already exists: {kijiwe.name}")
        except Exception as e:
            print(f"Error creating kijiwe {kijiwe_data['name']}: {str(e)}")

    print("\nTest kijiwe creation completed!")

if __name__ == '__main__':
    create_test_kijiwe()
