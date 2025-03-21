from datetime import timedelta
from venv import logger
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from operations.models import CustomUser, OTPCredit
from .models import OTPVerification
from .utils import create_otp_for_user, generate_otp, send_otp_via_sms
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def request_otp(request):
    """Request OTP for a user (Business, Operations, Customers, Riders)"""
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        
        if not phone:
            return JsonResponse({"error": "Phone number is required"}, status=400)

        try:
            user = CustomUser.objects.get(phone=phone)
            success = create_otp_for_user(user)
            if success:
                return JsonResponse({"message": "OTP sent successfully"}, status=200)
            else:
                return JsonResponse({"error": "Failed to send OTP"}, status=500)
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def normalize_phone(phone):
    """Ensures phone numbers are in international format (2557XXXXXXXX)."""
    cleaned_phone = ''.join(filter(str.isdigit, str(phone)))
    if not cleaned_phone.startswith('255'):
        if cleaned_phone.startswith('0'):
            cleaned_phone = '255' + cleaned_phone[1:]
        elif cleaned_phone.startswith('7'):
            cleaned_phone = '255' + cleaned_phone
    return cleaned_phone


@csrf_exempt
def verify_otp_view(request):
    """Handles OTP verification with improved debugging and session handling."""
    
    current_time = timezone.localtime(timezone.now())  
    logger.info(f"🕒 Django Local Time: {current_time}")

    if request.method == "GET":
        # Get phone number from URL query parameter
        phone_number = request.GET.get("phone", "")  
        if not phone_number:
            phone_number = request.session.get("otp_phone", "")
        
        # Store phone in session for later use
        if phone_number:
            request.session["otp_phone"] = phone_number
        
        return render(request, "user_verification/otp_verify.html", {"phone": phone_number})  

    elif request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        phone_number = request.POST.get("phone", "").strip()

   
        if not phone_number:
            phone_number = request.session.get("otp_phone", "")

        logger.info(f"📞 Received Phone Number (from frontend or session): '{phone_number}'")

        if not phone_number:
            return JsonResponse({"error": "Phone number is required for OTP verification."}, status=400)

       
        normalized_phone = normalize_phone(phone_number)
        logger.info(f"📞 Normalized Phone Number: '{normalized_phone}'")

        try:
            user = CustomUser.objects.get(phone=normalized_phone)
            logger.info(f"Found User: {user.phone}")

            otp_record = OTPCredit.objects.filter(user=user).order_by('-otp_timestamp').first()

            if not otp_record:
                logger.warning(f" No OTP record found for user {normalized_phone}")
                return JsonResponse({"error": "OTP expired or not found. Request a new one."}, status=400)

            otp_expiry_time = timezone.localtime(otp_record.otp_expiry)
            logger.info(f"🔢 Stored OTP: {otp_record.otp}, Expiry: {otp_expiry_time}, Now: {current_time}")

            if current_time > otp_expiry_time:
                logger.warning(" OTP has expired!")
                return JsonResponse({"error": "OTP has expired. Request a new one."}, status=400)

            if str(otp_record.otp) != str(otp):
                logger.warning(" Invalid OTP entered!")
                return JsonResponse({"error": "Invalid OTP. Please try again."}, status=400)

            # Activate the user only after successful OTP verification
            if not user.is_active:
                user.is_active = True
                user.save()
                logger.info(f"User {user.phone} activated successfully after OTP verification")
           
            # Clear the OTP record after successful verification
            otp_record.delete()
            logger.info("OTP record cleared after successful verification")
        
            request.session.pop("otp_phone", None)

            logger.info("OTP Verified Successfully!")
            
            # Redirect based on user role
            if user.role == 'business_owner':
                return redirect('business:business_dashboard')
            elif user.role == 'customer':
                return redirect('customers:home')
            elif user.role == 'rider':
                return redirect('riders:dashboard')
            else:
                return redirect('operations:dashboard')

        except CustomUser.DoesNotExist:
            logger.error(f" User with phone {normalized_phone} not found!")
            return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({"error": "Invalid request method."}, status=405)



@csrf_exempt
def resend_otp(request):
    """Handles resending OTP for a user"""
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()

        if not phone:
            return JsonResponse({"error": "Phone number is required"}, status=400)

        try:
            user = CustomUser.objects.get(phone=phone)
            otp_record = OTPVerification.objects.filter(user=user).order_by('-otp_timestamp').first()

            # ✅ Prevent spamming - Allow resend only after 60 seconds
            if otp_record and (timezone.now() - otp_record.otp_timestamp).seconds < 60:
                return JsonResponse({"error": "Please wait before requesting a new OTP."}, status=400)

            # ✅ Generate a new OTP and update expiry time
            new_otp = generate_otp()
            expiry_time = timezone.now() + timedelta(minutes=10)

            OTPVerification.objects.create(user=user, otp=new_otp, otp_expiry=expiry_time)

            # ✅ Send OTP via SMS
            success = send_otp_via_sms(phone, new_otp)

            if success:
                return JsonResponse({"message": "OTP resent successfully."}, status=200)
            else:
                return JsonResponse({"error": "Failed to resend OTP."}, status=500)

        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({"error": "Invalid request method."}, status=405)