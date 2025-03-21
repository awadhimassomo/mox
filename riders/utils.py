from math import radians, sin, cos, sqrt, atan2
import random
import requests
import json
from django.conf import settings

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in meters.
    """
    R = 6371000  # Earth's radius in meters

    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def get_nearby_riders(latitude, longitude, max_distance=2):
    """
    Get riders within max_distance kilometers of the given coordinates
    Returns list of riders with their distance from the point
    """
    from .models import Rider
    
    nearby_riders = []
    all_riders = Rider.objects.filter(is_active=True)
    
    for rider in all_riders:
        if rider.latitude and rider.longitude:
            distance = calculate_distance(
                float(latitude), 
                float(longitude),
                float(rider.latitude), 
                float(rider.longitude)
            )
            
            if distance / 1000 <= max_distance:  # Convert meters to kilometers
                nearby_riders.append({
                    'rider': rider,
                    'distance': round(distance / 1000, 2)  # Convert meters to kilometers
                })
    
    # Sort by distance
    return sorted(nearby_riders, key=lambda x: x['distance'])

def generate_otp(length=6):
    """Generate a random OTP of specified length."""
    digits = "0123456789"
    otp = ""
    for _ in range(length):
        otp += random.choice(digits)
    return otp

def send_otp_via_sms(phone_number, otp):
    """Send OTP via SMS using the messaging service."""
    try:
        # Format phone number to remove any '+' prefix
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        url = 'https://messaging-service.co.tz/api/sms/v1/text/single'
        headers = {
            'Authorization': "Basic YXRoaW06TWFtYXNob2tv",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        message = f"Your Mandood verification code is: {otp}. Valid for 10 minutes."
        
        payload = {
            "from": "MANDOOD",
            "to": phone_number,
            "text": message
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return False
