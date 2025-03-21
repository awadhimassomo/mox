import random
import uuid
import requests
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import CustomUser, OTPCredit
from .serializers import SendOTPSerializer, ResendOTPSerializer, VerifyOTPSerializer
from business.models import Business
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        personal_number = serializer.validated_data['personal_number']
        business_id = serializer.validated_data['business_id']

        try:
            user = CustomUser.objects.get(phone=personal_number)
            business = Business.objects.get(id=business_id, owner=user)

            otp_credit, created = OTPCredit.objects.get_or_create(user=user, business=business)

            # Check if we can send a new OTP
            if not created and not otp_credit.can_resend():
                return Response(
                    {"error": "Please wait 60 seconds before requesting a new OTP"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            otp = generate_otp()
            otp_credit.otp = otp
            otp_credit.otp_timestamp = timezone.now()
            otp_credit.otp_expiry = timezone.now() + timedelta(minutes=10)
            otp_credit.save()

            if send_otp_via_sms(personal_number, otp):
                return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Failed to send OTP"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except CustomUser.DoesNotExist:
            return Response({"error": "Personal number not found"}, status=status.HTTP_404_NOT_FOUND)
        except Business.DoesNotExist:
            return Response({"error": "Business not found or not associated with this user"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in SendOTPView: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt  
class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info("Received OTP resend request")
        serializer = ResendOTPSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"Serializer validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phoneNumber']
        logger.debug(f"Validated phone number: {phone_number}")

        try:
            user = CustomUser.objects.get(phone=phone_number)
            logger.debug(f"User found: {user}")

            try:
                otp_credit = OTPCredit.objects.get(user=user)
                logger.debug(f"OTP record found: {otp_credit}")

                if not otp_credit.can_resend():
                    logger.warning("OTP resend requested too soon")
                    return Response(
                        {"error": "Please wait 60 seconds before requesting a new OTP"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Generate a new OTP and update the expiry time
                otp = generate_otp()
                otp_credit.otp = otp
                otp_credit.otp_expiry = timezone.now() + timedelta(minutes=10)
                otp_credit.otp_timestamp = timezone.now()
                otp_credit.save()
                logger.info(f"OTP updated and saved: {otp}")

                # Send OTP via SMS
                if send_otp_via_sms(phone_number, otp):
                    logger.info("OTP sent successfully via SMS")
                    return Response({"message": "OTP resent successfully"}, status=status.HTTP_200_OK)
                else:
                    logger.error("Failed to send OTP via SMS")
                    return Response({"error": "Failed to resend OTP"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except OTPCredit.DoesNotExist:
                logger.error("No OTP record found for this user")
                return Response({"error": "No OTP record found for this user"}, status=status.HTTP_404_NOT_FOUND)

        except CustomUser.DoesNotExist:
            logger.error("Personal number not found")
            return Response({"error": "Personal number not found"}, status=status.HTTP_404_NOT_FOUND)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        personal_number = serializer.validated_data['personal_number']
        business_id = serializer.validated_data['business_id']
        otp = serializer.validated_data['otp']

        try:
            user = CustomUser.objects.get(phone=personal_number)
            business = Business.objects.get(id=business_id, owner=user)
            otp_credit = OTPCredit.objects.get(user=user, business=business)

            if otp_credit.is_expired():
                return Response({"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)

            if otp_credit.otp != otp:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

            # Clear the OTP after successful verification
            otp_credit.otp = None
            otp_credit.otp_expiry = None
            otp_credit.save()

            return Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response({"error": "Personal number not found"}, status=status.HTTP_404_NOT_FOUND)
        except Business.DoesNotExist:
            return Response({"error": "Business not found or not associated with this user"}, status=status.HTTP_404_NOT_FOUND)
        except OTPCredit.DoesNotExist:
            return Response({"error": "No OTP found for this user"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in VerifyOTPView: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def generate_otp():
    """Generate a 5-digit OTP."""
    return str(random.randint(10000, 99999)).zfill(5)

def generate_reference():
    """Generate a unique reference for SMS tracking."""
    return f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def send_otp_via_sms(phone_number, otp):
    """Send OTP via SMS using the messaging service."""
    try:
        from_ = "OTP"  # Sender name
        url = 'https://messaging-service.co.tz/api/sms/v1/text/single'
        headers = {
            'Authorization': "Basic YXRoaW06TWFtYXNob2tv",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        reference = generate_reference()

        # Clean phone number
        cleaned_phone = ''.join(filter(str.isdigit, phone_number))
        if not cleaned_phone.startswith('255'):
            if cleaned_phone.startswith('0'):
                cleaned_phone = '255' + cleaned_phone[1:]
            elif cleaned_phone.startswith('7'):
                cleaned_phone = '255' + cleaned_phone

        payload = {
            "from": from_,
            "to": cleaned_phone,
            "text": f"Your OTP is {otp}. Valid for 10 minutes.",
            "reference": reference,
        }

        logger.info(f"Sending OTP to: {cleaned_phone}, Reference: {reference}")
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            logger.info("OTP message sent successfully!")
            return True
        else:
            logger.error(f"Failed to send OTP message. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f'Error sending OTP: {e}')
        return False
