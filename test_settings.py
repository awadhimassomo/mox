from pathlib import Path
import os
from decouple import config

BASE_DIR = Path(__file__).resolve().parent

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

try:
    from django.db import connections
    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT 1')
        print("Database connection successful!")
except Exception as e:
    print(f"Error connecting to database: {e}")
