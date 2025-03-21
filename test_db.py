import psycopg2
from decouple import config

try:
    conn = psycopg2.connect(
        dbname=config('DB_NAME'),
        user=config('DB_USER'),
        password=config('DB_PASSWORD'),
        host=config('DB_HOST'),
        port=config('DB_PORT')
    )
    print("Database connection successful!")
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")
