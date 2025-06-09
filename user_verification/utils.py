import random
import requests
import uuid
from django.utils import timezone
from datetime import timedelta
from .models import OTPVerification

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def generate_reference():
    """Generate a unique reference ID"""
    return str(uuid.uuid4())

def send_otp_via_sms(phone, otp):
    """Send OTP via SMS using an API"""
    try:
        from_ = "OTP"  # Sender name
        url = 'https://messaging-service.co.tz/api/sms/v1/text/single'
        headers = {
            'Authorization': "Basic YXRoaW06TWFtYXNob2tv",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        reference = generate_reference()  # Generate the reference
        payload = {
            "from": from_,
            "to": phone,
            "text": f"Your OTP is {otp}",
            "reference": reference,
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False

def create_otp_for_user(user):
    """Generate and store OTP for a user"""
    otp = generate_otp()
    expiry_time = timezone.now() + timedelta(minutes=5)  # OTP expires in 5 minutes

    # Save OTP to database
    OTPVerification.objects.create(user=user, otp=otp, otp_expiry=expiry_time)

    # Send OTP via SMS
    return send_otp_via_sms(user.phone, otp)
