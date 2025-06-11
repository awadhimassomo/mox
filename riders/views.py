import uuid
from django.urls import reverse
import logging
import random
import string
import json
from django.db.models import Count, Sum, F, Q, FloatField
from django.db.models.functions import TruncDay, Coalesce
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.conf import settings
import math
import requests
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from customers.models import DeliveryAddress
from operations.models import Kijiwe, UserProfile, CustomUser, OTPCredit
from operations.serializers import ResendOTPSerializer
from orders.models import Order, OrderAssignmentGroup, OrderRiderAction
from .models import Rider
from .serializers import RiderSerializer

# Function to calculate distance between two points
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula."""
    # Convert to radians
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')  # Return infinity if any coordinate is missing
        
    lat1, lon1 = float(lat1), float(lon1)
    lat2, lon2 = float(lat2), float(lon2)
    
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Difference in coordinates
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance

class RiderViewSet(viewsets.ModelViewSet):
    queryset = Rider.objects.filter(is_available=True)
    serializer_class = RiderSerializer



logger = logging.getLogger(__name__)


def generate_otp():
    return str(random.randint(10000, 99999)).zfill(5)

def generate_reference():
    return str(uuid.uuid4())


@csrf_exempt
def rider_register(request):
    """Handles rider registration"""
    print("🚀 Received POST request")  # Debugging
    logger.info("🚀 Received POST request for rider registration.")

    if request.method == 'POST':
        try:
            print("📥 Extracting form data...")  # Debugging
            
            # Use request.POST to get form data instead of parsing JSON
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone = request.POST.get('phone')
            password = request.POST.get('password')
            region = request.POST.get('region')
            service_type = request.POST.get('service_type', 'delivery')  # Default to 'delivery' if not provided
            
            # Set transport type based on service type
            transport_type = request.POST.get('transport_type')
            if not transport_type and service_type != 'delivery' and service_type != 'moving_truck':
                # For non-delivery services, use the service type as transport type
                transport_type = service_type
                
            kijiwe_id = request.POST.get('kijiwe_id')  # match the name in the HTML form
            
            print(f"📋 Form Data - First Name: {first_name}, Last Name: {last_name}, Phone: {phone}, Password: {'YES' if password else 'NO'}")  # Debugging

            # Required fields validation
            required_fields = {
                'first_name': 'First name is required',
                'last_name': 'Last name is required',
                'phone': 'Phone number is required',
                'password': 'Password is required',
                'service_type': 'Please select a service type',
                'region': 'Please select your region'
            }
            
            errors = []
            for field, error_msg in required_fields.items():
                if not request.POST.get(field):
                    errors.append(error_msg)
            
            # Special validation for transport type when service type is delivery
            service_type = request.POST.get('service_type')
            if service_type == 'delivery' and not request.POST.get('transport_type'):
                errors.append('Please select your mode of transport')
            
            if errors:
                print(f"❌ Validation errors: {errors}")
                for error in errors:
                    messages.error(request, error)
                return redirect('riders:rider_register')

            # ✅ Ensure phone is formatted correctly
            cleaned_phone = ''.join(filter(str.isdigit, str(phone)))
            if not cleaned_phone.startswith('255'):
                if cleaned_phone.startswith('0'):
                    cleaned_phone = '255' + cleaned_phone[1:]
                elif cleaned_phone.startswith('7'):
                    cleaned_phone = '255' + cleaned_phone

            print(f"📞 Formatted Phone Number: {cleaned_phone}")  # Debugging

            # ✅ Check if phone number already exists
            if CustomUser.objects.filter(phone=cleaned_phone).exists():
                print(f"⚠️ Phone {cleaned_phone} is already registered!")  # Debugging
                messages.error(request, "Phone number already registered")
                return redirect('riders:rider_register')

            # ✅ Create the user
            print("🛠️ Creating new user...")  # Debugging
            user = CustomUser.objects.create_user(
                phone=cleaned_phone,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            request.session["otp_phone"] = cleaned_phone
            print(f"✅ User {cleaned_phone} created successfully!") 
            
            kijiwe_instance = None
            if kijiwe_id:
                try:
                    kijiwe_instance = Kijiwe.objects.get(id=int(kijiwe_id))  # ✅ Convert to integer
                    print(f"✅ Kijiwe Found: {kijiwe_instance}")  # Debugging
                except Kijiwe.DoesNotExist:
                    print(f"⚠️ Kijiwe with ID {kijiwe_id} not found.")
                    messages.error(request, "Invalid Kijiwe selected")
                    return redirect('riders:rider_register')
            
            rider = Rider.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                phone_number=cleaned_phone,
                password=make_password(password),  # Hash password
                region=region,  # Save the region
                service_type=service_type,  # Save service type
                transport_type=transport_type,  # Save transport type (only for delivery)
                kijiwe=kijiwe_instance,  # Save Kijiwe if applicable
            )
            print(f"✅ Rider Profile Created: {rider}")
            
            # Handle document uploads
            for field in ['id_photo', 'license_photo', 'latra_certificate', 'insurance_certificate', 'vehicle_photo']:
                if field in request.FILES:
                    setattr(rider, field, request.FILES[field])
            
            # Save the rider with documents
            rider.save()
            print(f"✅ Rider documents saved")

            # ✅ Log before sending OTP
            logger.info(f"📲 Attempting to send OTP to {cleaned_phone}")
            print(f"📲 Sending OTP to {cleaned_phone}...")  #
            
            otp = random.randint(100000, 999999)  # 6-digit OTP
            print(f"🔢 Generated OTP: {otp}") 
            
            expiry_time = timezone.now() + timezone.timedelta(minutes=5)  # 5 minutes expiry

            otp_entry, created = OTPCredit.objects.update_or_create(
                user=user,
                defaults={
                    "otp": otp,
                    "otp_timestamp": timezone.now(),
                    "otp_expiry": expiry_time
                }
            )
            print(f"🔢 OTP Entry: {otp_entry.otp}, Created: {created}")

            print(f"🔢 Generated OTP: {otp} (Saved in DB)") 
                
            # ✅ Generate and send OTP
            otp_sent = send_otp_via_sms(cleaned_phone, otp)

            if not otp_sent:
                logger.error(f"❌ Failed to send OTP to {cleaned_phone}")
                print("❌ OTP sending failed.")  # Debugging
                messages.error(request, "Failed to send OTP. Please try again.")
                return redirect('riders:rider_register')

            logger.info(f" OTP sent successfully to {cleaned_phone}")
            print(" OTP sent successfully.")  # Debugging

            # Redirect to OTP verification page with success message
            messages.success(request, "Registration successful! Please verify your phone number with the OTP sent.")
            return redirect('riders:verify_otp')

        except Exception as e:
            logger.error(f"🔥 Error in rider_register: {e}")
            print(f"🔥 Error in rider_register: {e}")  # Debugging
            messages.error(request, str(e))
            return redirect('riders:rider_register')

    print("🖥️ GET request received - rendering register page")  # Debugging
    return render(request, 'riders/rider_register.html')


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
        phone_number = request.GET.get("phone", "")  
        if not phone_number:
            phone_number = request.session.get("otp_phone", "")
        
        return render(request, "riders/otp_verify.html", {"phone": phone_number})  

    elif request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        phone_number = request.POST.get("phone", "").strip()

        logger.debug(f"Received OTP: {otp}, Phone Number: {phone_number}")

        if not phone_number:
            phone_number = request.session.get("otp_phone", "")

        logger.info(f"📞 Received Phone Number (from frontend or session): '{phone_number}'")

        if not phone_number:
            return redirect('riders:rider_register')

        normalized_phone = normalize_phone(phone_number)
        logger.info(f"📞 Normalized Phone Number: '{normalized_phone}'")

        try:
            user = CustomUser.objects.get(phone=normalized_phone)
            logger.info(f"Found User: {user.phone}")

            otp_record = OTPCredit.objects.filter(user=user).order_by('-otp_timestamp').first()

            if not otp_record:
                logger.warning(f" No OTP record found for user {normalized_phone}")
                messages.error(request, "OTP expired or not found. Request a new one.")
                return redirect('riders:rider_register')

            otp_expiry_time = timezone.localtime(otp_record.otp_expiry)
            logger.info(f"🔢 Stored OTP: {otp_record.otp}, Expiry: {otp_expiry_time}, Now: {current_time}")

            if str(otp_record.otp) != str(otp):
                logger.warning(" Invalid OTP entered!")
                messages.error(request, "Invalid OTP. Please try again.")
                return redirect('riders:verify_otp')

            user.is_active = True
            user.save()
            request.session.pop("otp_phone", None)

            logger.info("OTP Verified Successfully!")
            
            return redirect('riders:login')

        except CustomUser.DoesNotExist:
            logger.error(f" User with phone {normalized_phone} not found!")
            messages.error(request, "User not found")
            return redirect('riders:rider_register')

    return redirect('riders:rider_register')


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info("📩 Received OTP resend request")
        logger.debug(f"📄 Request data: {request.data}")

        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']  # ✅ Make sure field name is correct
            logger.debug(f"📞 Validated phone number: {phone}")

            try:
                user = CustomUser.objects.get(phone=phone)  # ✅ Ensure it matches User model
                logger.debug(f"✅ User found: {user}")

                otp_credit, created = OTPCredit.objects.get_or_create(user=user)

                # Check if the resend request is too soon
                if otp_credit.otp_timestamp and (timezone.now() - otp_credit.otp_timestamp).seconds < 60:
                    logger.warning("⚠️ OTP resend requested too soon")
                    return Response({"error": "OTP resend is allowed after 60 seconds"}, status=status.HTTP_400_BAD_REQUEST)

                # Generate a new OTP and update the expiry time
                otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP
                otp_credit.otp = otp
                otp_credit.otp_expiry = timezone.now() + timedelta(minutes=10)  # Reset expiry time
                otp_credit.otp_timestamp = timezone.now()
                otp_credit.save()  # ✅ Ensure OTP is saved

                logger.info(f"🔢 OTP updated and saved: {otp}")

                # Send OTP via SMS
                if send_otp_via_sms(phone, otp):
                    logger.info("✅ OTP sent successfully via SMS")
                    return Response({"message": "OTP resent successfully"}, status=status.HTTP_200_OK)
                else:
                    logger.error("❌ Failed to send OTP via SMS")
                    return Response({"error": "Failed to resend OTP"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except CustomUser.DoesNotExist:
                logger.error("❌ Personal number not found")
                return Response({"error": "Personal number not found"}, status=status.HTTP_404_NOT_FOUND)
        
        logger.error(f"❌ Serializer validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def send_otp_via_sms(phoneNumber, otp):
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
            "to": phoneNumber,
            "text": f"Your OTP are {otp}",
            "reference": reference,
        }

        # Print the phone number and reference before making the request
        print(f"Sending OTP to: {phoneNumber}, Reference: {reference}")

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print("OTP message sent successfully!")
            return True
        else:
            print("Failed to send OTP message.")
            print(response.status_code)
            print(response.text)
            return False
    except Exception as e:
        print(f'Error sending OTP: {e}')
        return False

 
def rider_login(request):
    """Handles rider login request"""
    if request.method == 'GET':
        return render(request, 'riders/rider_login.html')  # ✅ Render login template

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)  # ✅ Ensure request is JSON
            phone = data.get('phone_number')
            password = data.get('password')

            print(f"📞 Received phone number: {phone}")
            print(f"🔑 Received password: {'YES' if password else 'NO'}")

            if not phone or not password:
                return JsonResponse({"error": "Phone number and password are required"}, status=400)

            # ✅ Clean phone number for consistency
            cleaned_phone = ''.join(filter(str.isdigit, phone))
            print(f"📞 Cleaned phone number: {cleaned_phone}")

            # ✅ Print all phone numbers in the database to compare
            all_users = Rider.objects.values_list('phone_number', flat=True)
            print(f"📋 All Registered Phone Numbers: {list(all_users)}")

            # ✅ Check if the user exists
            try:
                user = CustomUser.objects.get(phone=cleaned_phone)
                print(f"✅ User found: {user.phone}")  # ✅ Debugging
            except CustomUser.DoesNotExist:
                print(f"❌ No user found with phone number: {cleaned_phone}")
                return JsonResponse({"error": "User not found"}, status=404)

            # ✅ Authenticate the user
            user = authenticate(request, username=user.phone, password=password)
            print(f"🔍 Authentication result: {'SUCCESS' if user else 'FAILURE'}")

            if user is not None:
                login(request, user)
                print("✅ Login successful")
                return JsonResponse({"success": True, "message": "Login successful", "user_id": user.id})
            else:
                print("❌ Invalid phone number or password")
                return JsonResponse({"error": "Invalid phone number or password"}, status=401)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

def rider_logout(request):
    logout(request)
    return redirect('riders:login') 

@login_required
def riders_list(request):
    """View for listing all riders"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        return render(request, 'riders/riderdashboard.html', {
            'region': user_profile.region
        })
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found')
        return redirect('dashboard_login')

@login_required
def rider_profile_view(request):
    """Renders the rider profile page and handles profile updates."""
    if not request.user.is_authenticated:
        return redirect('riders:login')
    try:
        rider = Rider.objects.get(user=request.user)
        
        if request.method == 'POST':
            # Handle profile image upload and other updates
            if 'profile_image' in request.FILES:
                rider.profile_image = request.FILES['profile_image']
            
            # Update other profile fields
            if request.POST.get('first_name'):
                request.user.first_name = request.POST.get('first_name')
            if request.POST.get('last_name'):
                request.user.last_name = request.POST.get('last_name')
            if request.POST.get('phone_number'):
                rider.phone_number = request.POST.get('phone_number')
                
            # Save changes
            request.user.save()
            rider.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('riders:profile')
            
        return render(request, 'riders/rider_profile.html', {'rider': rider})
    except Rider.DoesNotExist:
        return redirect('riders:login')


@login_required
def change_password(request):
    """Handles password change for riders"""
    if not request.user.is_authenticated:
        return redirect('riders:login')
    
    # Initialize context variables
    password_messages = []
    
    try:
        rider = Rider.objects.get(user=request.user)
        
        if request.method == 'POST':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validate input
            if not all([current_password, new_password, confirm_password]):
                password_messages.append({'type': 'error', 'text': 'All password fields are required.'})
            elif new_password != confirm_password:
                password_messages.append({'type': 'error', 'text': 'New passwords do not match.'})
            elif len(new_password) < 8:
                password_messages.append({'type': 'error', 'text': 'Password must be at least 8 characters long.'})
            else:
                # Check if current password is correct
                user = authenticate(username=request.user.username, password=current_password)
                if user is None:
                    password_messages.append({'type': 'error', 'text': 'Current password is incorrect.'})
                else:
                    # Change password
                    user.set_password(new_password)
                    user.save()
                    password_messages.append({'type': 'success', 'text': 'Password changed successfully. Please log in again with your new password.'})
                    # Log the user out so they can log in with new password
                    logout(request)
                    return redirect('riders:login')
        
        # Render the profile page with password change messages
        return render(request, 'riders/rider_profile.html', {
            'rider': rider, 
            'password_messages': password_messages
        })
    except Rider.DoesNotExist:
        return redirect('riders:login')

@login_required
def rider_orders_view(request):
    """Renders the rider orders page."""
    if not request.user.is_authenticated:
        return redirect('riders:login')
    return render(request, 'riders/rider_orders.html')

@login_required
def rider_earnings_view(request):
    """Renders the rider earnings page."""
    if not request.user.is_authenticated:
        return redirect('riders:login')
    
    try:
        rider = Rider.objects.get(user=request.user)
        return render(request, 'riders/rider_earnings.html', {'rider': rider})
    except Rider.DoesNotExist:
        return redirect('riders:login')
    except Exception as e:
        logger.error(f"Error in rider earnings view: {str(e)}")
        messages.error(request, f"Error loading earnings page: {str(e)}")
        return render(request, 'riders/rider_earnings.html', {'error': str(e)})

@login_required
def rider_history_view(request):
    """Renders the rider history page."""
    if not request.user.is_authenticated:
        return redirect('riders:login')
    return render(request, 'riders/rider_history.html')

@login_required
def rider_dashboard(request):
    """Renders the rider dashboard page."""
    if not request.user.is_authenticated:
        return redirect('riders:login')
    try:
        from django.db.models import Q
        rider = Rider.objects.get(user=request.user)
        
        # Log rider information
        logger.info(f"Dashboard: Rider {rider.id} - {rider.user.first_name} {rider.user.last_name}")
        logger.info(f"Dashboard: Rider location: Lat {rider.latitude}, Lng {rider.longitude}, Region: {rider.region}")
        
        # Get orders assigned to this rider through OrderAssignmentGroup
        from orders.models import Order, OrderAssignmentGroup
        
        # Get orders currently assigned to this rider
        assignment_groups = OrderAssignmentGroup.objects.filter(
            riders=rider,
            is_active=True
        )
        
        processing_orders = Order.objects.filter(
            rider=rider,
            status='processing'
        ).order_by('-created_at')

        ready_for_pickup_orders = Order.objects.filter(
            rider=rider,
            status='ready_for_pickup'
        ).order_by('-created_at')

        in_transit_orders = Order.objects.filter(
            rider=rider,
            status='in_transit'
        ).order_by('-created_at')
        
        # Collect data for completed orders
        completed_orders = Order.objects.filter(
            rider=rider,
            status__in=['delivered', 'cancelled']
        ).distinct().order_by('-created_at')
        
        # Get all available orders (available) not already assigned to this rider
        available_orders = Order.objects.filter(
            Q(status__iexact='available') | Q(status__iexact='pending')
        ).exclude(
            rider__isnull=False  # Exclude orders that already have a rider
        ).order_by('-created_at')
        
        # Function to check if coordinate is valid
        def is_valid_coordinate(coord):
            if coord is None:
                return False
            try:
                float_val = float(coord)
                return float_val != 0
            except (ValueError, TypeError):
                return False
        
        # Get rider coordinates
        rider_lat = rider.latitude
        rider_lng = rider.longitude
        rider_region = rider.region if hasattr(rider, 'region') else None
        
        # Process available orders by distance
        nearby_orders = []  # Within 300m
        same_region_orders = []  # Same region but beyond 300m
        other_region_orders = []  # Different region
        
        for order in available_orders:
            try:
                business_region = order.business.region if order.business and hasattr(order.business, 'region') else "Unknown"
                order.region = business_region
                
                # Only consider orders in the same region as the rider OR orders without region
                if not (rider_region and business_region and rider_region == business_region):
                    logger.info(f"Skipping order #{order.id} - different region ({business_region} vs {rider_region})")
                    continue
                
                # For orders in same region or unknown region, check distance
                pickup_lat = order.pickup_latitude
                pickup_lng = order.pickup_longitude
                
                # If no pickup coordinates but we have business coordinates, use those
                if not is_valid_coordinate(pickup_lat) or not is_valid_coordinate(pickup_lng):
                    if order.business and is_valid_coordinate(order.business.latitude) and is_valid_coordinate(order.business.longitude):
                        pickup_lat = order.business.latitude
                        pickup_lng = order.business.longitude
                        logger.info(f"Using business coordinates for order {order.id}: {pickup_lat}, {pickup_lng}")
                
                # Calculate distance if we have coordinates
                if is_valid_coordinate(rider_lat) and is_valid_coordinate(rider_lng) and is_valid_coordinate(pickup_lat) and is_valid_coordinate(pickup_lng):
                    distance = calculate_distance(
                        float(rider_lat), float(rider_lng),
                        float(pickup_lat), float(pickup_lng)
                    )
                    
                    # Format distance for display
                    order.distance = f"{distance:.1f} km"
                    logger.info(f"Order #{order.id} distance: {distance:.1f} km")
                    
                    # IMPORTANT: Categorization by distance
                    if distance <= 0.3:  # Within 300m
                        nearby_orders.append(order)
                        logger.info(f"Order #{order.id} is nearby ({distance:.1f} km)")
                    else:
                        same_region_orders.append(order)
                        logger.info(f"Order #{order.id} is in same region but far ({distance:.1f} km)")
                else:
                    # No valid coordinates for distance calculation
                    logger.warning(f"No valid coordinates to calculate distance for order #{order.id}")
                    same_region_orders.append(order)
                
                # Format the drop-off coordinates for display 
                delivery_lat = order.delivery_latitude
                delivery_lng = order.delivery_longitude
                
                # Check if we need to use business coordinates as fallback
                if not is_valid_coordinate(delivery_lat) or not is_valid_coordinate(delivery_lng):
                    if order.business and is_valid_coordinate(order.business.latitude) and is_valid_coordinate(order.business.longitude):
                        delivery_lat = order.business.latitude
                        delivery_lng = order.business.longitude
                
                # Set the dropoff_location attribute
                has_valid_coords = is_valid_coordinate(delivery_lat) and is_valid_coordinate(delivery_lng)
                order.dropoff_location = f"{delivery_lat}, {delivery_lng}" if has_valid_coords else "No coordinates available"
                
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
                other_region_orders.append(order)  # Default to other region if we can't process
        
        logger.info(f"Categorized orders: Nearby ({len(nearby_orders)}), Same Region But Far ({len(same_region_orders)}), Other Regions ({len(other_region_orders)})")
        
        # Format processing orders with coordinates
        processing_orders = processing_orders.filter(status__in=['in_transit', 'assigned', 'proceeded'])
        
        for order in processing_orders:
            delivery_lat = order.delivery_latitude
            delivery_lng = order.delivery_longitude
            
            if not is_valid_coordinate(delivery_lat) or not is_valid_coordinate(delivery_lng):
                if order.business and is_valid_coordinate(order.business.latitude) and is_valid_coordinate(order.business.longitude):
                    delivery_lat = order.business.latitude
                    delivery_lng = order.business.longitude
            
            has_valid_coords = is_valid_coordinate(delivery_lat) and is_valid_coordinate(delivery_lng)
            order.dropoff_location = f"{delivery_lat}, {delivery_lng}" if has_valid_coords else "No coordinates available"
        
        context = {
            'rider': rider,
            'incoming_orders': nearby_orders,  # Only nearby orders (300m) show on main dashboard
            'processing_orders': processing_orders,
            'ready_for_pickup_orders': ready_for_pickup_orders,
            'in_transit_orders': in_transit_orders,
            'completed_orders': completed_orders,
            'same_region_orders_count': len(same_region_orders),
            'other_region_orders_count': len(other_region_orders),
            'total_more_orders': len(same_region_orders) + len(other_region_orders)
        }
        
        return render(request, 'riders/riderdashboard.html', context)
    except Rider.DoesNotExist:
        return redirect('riders:login')
    except Exception as e:
        logger.error(f"Error in rider dashboard: {str(e)}")
        messages.error(request, f"Error retrieving orders: {str(e)}")
        return render(request, 'riders/riderdashboard.html', {'error': str(e)})

class UpdateRiderLocation(APIView):
    """API View for updating rider location."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            rider = Rider.objects.get(user=request.user)
            rider.latitude = request.data.get('latitude')
            rider.longitude = request.data.get('longitude')
            rider.save()
            return Response({'status': 'success'})
        except Rider.DoesNotExist:
            return Response({'status': 'error', 'message': 'Rider not found'}, status=404)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=500)

@api_view(['GET'])
def get_kijiwe_locations(request):
    """Fetch Kijiwe locations based on the selected region"""
    region = request.query_params.get('region')

    if not region:
        return Response({"error": "Region parameter is required"}, status=400)

    # Query the database for Kijiwe objects with matching region
    kijiwe_locations = Kijiwe.objects.filter(region=region).order_by('name')
    
    if not kijiwe_locations.exists():
        # Fallback to hardcoded values if no database entries exist
        hardcoded_locations = {
            'dar_es_salaam': ['Kariakoo', 'Sinza', 'Mbezi', 'Tegeta', 'Ubungo'],
            'arusha': ['Sakina', 'Ngarenaro', 'Kijenge', 'Sanawari'],
            'mwanza': ['Nyamagana', 'Ilemela', 'Mabatini', 'Igogo'],
            'dodoma': ['Makole', 'Area C', 'Chamwino'],
            'tanga': ['Ngamiani', 'Chumbageni', 'Tangasisi'],
            'mbeya': ['Iyunga', 'Mbalizi', 'Forest'],
            'morogoro': ['Kihonda', 'Sabasaba', 'Mazimbu'],
            'zanzibar': ['Stone Town', 'Nungwi', 'Paje']
        }
        
        if region in hardcoded_locations:
            return Response([
                {"id": i, "name": name} 
                for i, name in enumerate(hardcoded_locations[region], 1)
            ])
        return Response([], status=200)  # Empty list if no locations found

    # Return a list of dictionaries with id and name
    locations_data = [
        {"id": kijiwe.id, "name": kijiwe.name} 
        for kijiwe in kijiwe_locations
    ]
    
    return Response(locations_data, status=200)

@api_view(['POST'])
def rider_update_profile_api(request):
    """API endpoint for updating rider profile."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    try:
        rider = Rider.objects.get(user=request.user)
        rider.phone_number = request.data.get('phone_number', rider.phone_number)
        rider.save()
        
        user = request.user
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.save()
        
        return JsonResponse({'success': True})
    except Rider.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rider not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def rider_login_api(request):
    """API endpoint for rider login."""
    phone = request.data.get('phone_number')
    password = request.data.get('password')

    # Clean phone number
    cleaned_phone = ''.join(filter(str.isdigit, phone))
    if not cleaned_phone.startswith('255'):
        if cleaned_phone.startswith('0'):
            cleaned_phone = '255' + cleaned_phone[1:]
        elif cleaned_phone.startswith('7'):
            cleaned_phone = '255' + cleaned_phone

    try:
        # Authenticate user
        user = authenticate(request, phone=cleaned_phone, password=password)

        if user is not None:
            if not user.is_active:
                return Response({
                    'status': 'error',
                    'message': 'Account is not active'
                }, status=status.HTTP_403_FORBIDDEN)

            # Check if user is a rider
            try:
                rider = Rider.objects.get(user=user)
            except Rider.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'User is not a rider'
                }, status=status.HTTP_403_FORBIDDEN)

            # Log the user in
            login(request, user)

            # Return user data
            return Response({
                'status': 'success',
                'message': 'Login successful',
                'data': {
                    'user_id': user.id,
                    'phone': user.phone,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'region': user.region,
                    'rider_id': rider.id,
                    'is_available': rider.is_available,
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
def update_location(request):
    """Update a rider's location based on their current coordinates."""
    from django.db.models import Q  # Ensure Q is imported here too
    if request.method == 'POST':
        # Get coordinates from request
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Get the logged-in rider
        if request.user.is_authenticated:
            rider = Rider.objects.get(user=request.user)
            rider.latitude = latitude
            rider.longitude = longitude
            rider.save()

            print(f"✅ Rider {rider.user.get_full_name()} Location Updated - New Location: ({latitude}, {longitude})")
            return JsonResponse({"message": "Location updated successfully", "latitude": latitude, "longitude": longitude}, status=200)

        else:
            print("❌ Unauthorized request. User is not authenticated.")
            return JsonResponse({"error": "Unauthorized"}, status=403)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def update_rider_location(request):
    """Updates the rider's location and prints/logs the received data."""
    if request.method == "POST":
        try:
            # Import Q here to ensure it's available
            from django.db.models import Q
            
            data = json.loads(request.body)
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            is_online = data.get("is_online", True)  # Default to True if not provided

            # Print for debugging
            print(f"📍 Received Location Update - Latitude: {latitude}, Longitude: {longitude}, Online: {is_online}")

            if not latitude or not longitude:
                return JsonResponse({"error": "Latitude and Longitude are required"}, status=400)

            # Get the logged-in rider
            if request.user.is_authenticated:
                rider = Rider.objects.get(user=request.user)
                rider.latitude = latitude
                rider.longitude = longitude
                rider.is_available = is_online  # Update availability status
                rider.save()

                print(f"✅ Rider {rider.user.get_full_name()} Location Updated - New Location: ({latitude}, {longitude}), Online: {is_online}")
                return JsonResponse({
                    "message": "Location updated successfully", 
                    "latitude": latitude, 
                    "longitude": longitude,
                    "is_online": is_online
                }, status=200)

            else:
                print("❌ Unauthorized request. User is not authenticated.")
                return JsonResponse({"error": "Unauthorized"}, status=403)

        except json.JSONDecodeError:
            print("❌ Error: Invalid JSON format received")
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Rider.DoesNotExist:
            print("❌ Error: Rider not found")
            return JsonResponse({"error": "Rider not found"}, status=404)
        except Exception as e:
            print(f"🔥 Unexpected Error: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@login_required
def accept_order_assignment(request, order_id):
    """
    Handles a rider accepting an order assignment
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method")
        return redirect('riders:dashboard')
    
    try:
        # Get the rider
        rider = request.user.rider
        
        # Get the order
        from orders.models import Order
        order = get_object_or_404(Order, id=order_id)
        
        # Check if the order is still in 'assigned' status
        if order.status != 'ASSIGNED':
            messages.error(request, "This order is no longer available for assignment")
            return redirect('riders:dashboard')
        
        # Check if the rider is in any assignment group for this order
        from customers.models import OrderAssignmentGroup
        assignment_groups = OrderAssignmentGroup.objects.filter(
            riders=rider
        )
        
        if not assignment_groups.exists():
            messages.error(request, "You are not assigned to this order")
            return redirect('riders:dashboard')
        
        # Assign the order to this rider
        order.rider = rider
        order.status = 'processing'  # Change to processing instead of pending
        order.save()

        # Record the rider action
        OrderRiderAction.record_action(
            order=order,
            rider=rider,
            action_type='accepted',
            notes="Order accepted by rider",
            lat=rider.latitude,
            lng=rider.longitude
        )
        
        messages.success(request, f"You have been assigned to order #{order.order_number}")
        return redirect('riders:order_detail', order_id=order.id)
    
    except Exception as e:
        logger.error(f"Error accepting order assignment: {str(e)}", exc_info=True)
        messages.error(request, f"Error accepting order: {str(e)}")
        return redirect('riders:dashboard')

@login_required
def accept_order_api(request, order_id):
    """API endpoint for a rider accepting an order"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Only POST method is allowed"}, status=405)
    
    try:
        rider = Rider.objects.get(user=request.user)
        from orders.models import Order, OrderAssignmentGroup, OrderRiderAction
        
        # Get the order
        order = get_object_or_404(Order, id=order_id)
        
        # Make sure the order is in 'available' or 'pending' status
        if order.status.lower() not in ['available', 'pending']:
            return JsonResponse({
                "success": False, 
                "error": f"Order is not available for assignment. Current status: {order.status}. Only AVAILABLE or PENDING orders can be accepted."
            })

        # Get rider location for tracking
        rider_location_lat = None
        rider_location_lng = None
        if hasattr(rider, 'latitude') and hasattr(rider, 'longitude'):
            rider_location_lat = rider.latitude
            rider_location_lng = rider.longitude
        
        # Create an assignment group if it doesn't exist
        group, created = OrderAssignmentGroup.objects.get_or_create(
            order=order,
            defaults={'is_active': True}
        )
        
        # Add this rider to the assignment
        group.riders.add(rider)
        
        # Directly assign the rider to the order
        order.rider = rider
        
        # Update order status to processing
        order.status = 'processing'  # Change to processing instead of pending
        order.save()
        
        # Record the action using the new OrderRiderAction model
        OrderRiderAction.record_action(
            order=order,
            rider=rider,
            action_type='accepted',
            notes='Rider accepted order for gas delivery',
            lat=rider_location_lat,
            lng=rider_location_lng
        )
        
        # Log this assignment
        logger.info(f"Rider {rider.id} ({rider.user.get_full_name()}) accepted order {order.id}")
        
        return JsonResponse({
            "success": True,
            "message": f"You have successfully accepted order #{order.id}",
            "order_id": order.id,
            "order_number": order.order_number
        })
        
    except Order.DoesNotExist:
        return JsonResponse({"success": False, "error": "Order not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in accept order API: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@login_required
def order_detail(request, order_id):
    """
    View for displaying order details to a rider
    """
    try:
        # Get the order
        from orders.models import Order
        order = get_object_or_404(Order, id=order_id)
        
        # Safely check if the rider is assigned to this order or if it's in the assignment pool
        rider_assigned = False
        try:
            if hasattr(order, 'rider') and order.rider and order.rider == request.user.rider:
                # Rider is already assigned to this order
                rider_assigned = True
        except AttributeError:
            logger.warning(f"Order {order_id} has no rider attribute")
            # Continue with rider_assigned as False
            
        if not rider_assigned:
            # Check if the rider is in any assignment group for this order
            from customers.models import OrderAssignmentGroup
            is_assignable = OrderAssignmentGroup.objects.filter(
                riders=request.user.rider
            ).exists()
            
            if not is_assignable and order.status != 'ASSIGNED':
                messages.error(request, "You don't have access to this order")
                return redirect('riders:dashboard')
        
        context = {
            'order': order,
            'title': f'Order #{order.order_number}'
        }
        
        return render(request, 'riders/order_detail.html', context)
    
    except Exception as e:
        logger.error(f"Error viewing order details: {str(e)}", exc_info=True)
        messages.error(request, f"Error viewing order: {str(e)}")
        return redirect('riders:dashboard')

@login_required
def update_order_status(request, order_id):
    """
    Handles updating the status of an order by a rider
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method")
        return redirect('riders:dashboard')
    
    try:
        # Get the order
        from orders.models import Order
        order = get_object_or_404(Order, id=order_id)
        
        # Safely check if the rider is assigned to this order
        rider_assigned = False
        try:
            if hasattr(order, 'rider') and order.rider and order.rider == request.user.rider:
                rider_assigned = True
        except AttributeError:
            logger.warning(f"Order {order_id} has no rider attribute when updating status")
            
        if not rider_assigned:
            messages.error(request, "You are not assigned to this order")
            return redirect('riders:dashboard')
        
        # Get the new status
        new_status = request.POST.get('status')
        
        # Validate the status transition
        valid_transitions = {
            'ASSIGNED': ['IN_TRANSIT'],
            'IN_TRANSIT': ['DELIVERED']
        }
        
        current_status = order.status
        if current_status not in valid_transitions or new_status not in valid_transitions.get(current_status, []):
            messages.error(request, "Invalid status transition")
            return redirect('riders:dashboard')
        
        # Update the order status
        order.status = new_status
        
        # If the order is being marked as delivered, update the delivery time
        if new_status == 'DELIVERED':
            order.delivered_at = timezone.now()
        
        order.save()
        
        # Add a success message
        status_messages = {
            'IN_TRANSIT': 'Delivery started',
            'DELIVERED': 'Delivery completed successfully'
        }
        
        messages.success(request, status_messages.get(new_status, f"Order status updated to {new_status}"))
        
        # Redirect back to the order detail page
        return redirect('riders:order_detail', order_id=order.id)
    
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}", exc_info=True)
        messages.error(request, f"Error updating order status: {str(e)}")
        return redirect('riders:order_detail', order_id=order_id)

@login_required
def dashboard_data(request):
    """API endpoint for the rider dashboard data."""
    try:
        from django.db.models import Q
        rider = Rider.objects.get(user=request.user)
        
        # Get orders assigned to this rider
        assigned_orders = Order.objects.filter(
            rider=rider,
            status__in=['assigned', 'picked_up']
        )
        
        # Get completed orders
        completed_orders = Order.objects.filter(
            rider=rider,
            status__in=['delivered', 'cancelled']
        ).order_by('-updated_at')[:10]
        
        # Prepare data
        rider_data = {
            'name': rider.user.get_full_name(),
            'id': rider.id,
            'assigned_orders': assigned_orders.count(),
            'completed_orders': completed_orders.count(),
            'latitude': rider.latitude,
            'longitude': rider.longitude,
            'is_available': rider.is_available,  # Add availability status
            'last_location_update': rider.last_location_update.isoformat() if rider.last_location_update else None
        }
        
        return JsonResponse(rider_data)
    except Rider.DoesNotExist:
        return JsonResponse({'error': 'Rider not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in dashboard data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def record_penalty_api(request, order_id):
    """
    API endpoint for recording a penalty when a rider doesn't respond to an order within the time limit.
    """
    from django.db.models import F
    from riders.models import RiderPenalty
    
    if not request.user.is_authenticated or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Unauthorized or invalid method'}, status=401)
    
    try:
        rider = Rider.objects.get(user=request.user)
        order = Order.objects.get(id=order_id)
        
        # Create a penalty record
        penalty = RiderPenalty.objects.create(
            rider=rider,
            order=order,
            penalty_type='MISSED_ORDER',
            description='Failed to respond to gas delivery order within 120 minutes',
            points=1
        )
        
        # Update rider's total penalties
        rider.total_penalties = F('total_penalties') + 1
        rider.save(update_fields=['total_penalties'])
        
        return JsonResponse({
            'success': True, 
            'message': 'Penalty recorded successfully',
            'penalty_id': penalty.id
        })
    except Rider.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rider not found'}, status=404)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except Exception as e:
        logger.error(f"Error recording penalty: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def complete_order_api(request, order_id):
    """
    API endpoint for marking a gas delivery order as completed.
    """
    if not request.user.is_authenticated or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Unauthorized or invalid method'}, status=401)
    
    try:
        rider = Rider.objects.get(user=request.user)
        from orders.models import Order, OrderRiderAction
        order = Order.objects.get(id=order_id)
        
        # Check if this rider is assigned to this order or if the order is in the assignment pool
        if not order.assignment_groups.filter(riders=rider, is_active=True).exists():
            return JsonResponse({
                'success': False, 
                'error': 'You are not assigned to this order'
            }, status=403)
        
        # Get rider location if available
        rider_location_lat = None
        rider_location_lng = None
        if hasattr(rider, 'latitude') and hasattr(rider, 'longitude'):
            rider_location_lat = rider.latitude
            rider_location_lng = rider.longitude
        
        # Record the completion action using the OrderRiderAction model
        OrderRiderAction.record_action(
            order=order,
            rider=rider,
            action_type='completed',
            notes=f"Rider completed gas delivery",
            lat=rider_location_lat,
            lng=rider_location_lng
        )
        
        # The record_action method already updates the order, but we'll add more fields if needed
        if not hasattr(order, 'delivery_completed_at') or not order.delivery_completed_at:
            order.delivery_completed_at = timezone.now()
            order.save(update_fields=['delivery_completed_at'])
        
        # Log the completion
        logger.info(f"Order {order.id} marked as completed by rider {rider.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Gas delivery order marked as completed'
        })
    except Rider.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rider not found'}, status=404)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except Exception as e:
        logger.error(f"Error completing order: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def debug_coordinates(request):
    """Debug endpoint to check delivery coordinates directly from the database"""
    from orders.models import Order
    
    try:
        # Get a sample of recent orders
        recent_orders = Order.objects.all().order_by('-created_at')[:10]
        
        orders_data = []
        for order in recent_orders:
            # Get all available location fields
            order_data = {
                'id': order.id,
                'order_number': order.order_number,
                'delivery_latitude': str(order.delivery_latitude),
                'delivery_longitude': str(order.delivery_longitude),
                'delivery_location': order.delivery_location,
                'pickup_latitude': str(order.pickup_latitude) if hasattr(order, 'pickup_latitude') else 'N/A',
                'pickup_longitude': str(order.pickup_longitude) if hasattr(order, 'pickup_longitude') else 'N/A',
            }
            
            # Check if business has coordinates
            if order.business:
                order_data['business_latitude'] = str(order.business.latitude) if hasattr(order.business, 'latitude') else 'N/A' 
                order_data['business_longitude'] = str(order.business.longitude) if hasattr(order.business, 'longitude') else 'N/A'
                order_data['business_address'] = order.business.address if hasattr(order.business, 'address') else 'N/A'
            else:
                order_data['business_info'] = 'No business associated'
            
            orders_data.append(order_data)
        
        # Return the debug data
        return JsonResponse({
            'orders_data': orders_data,
            'message': 'This is debug information to help diagnose coordinate issues.'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    



@login_required
def rider_earnings_stats_api(request):
    """API endpoint for rider earnings summary and stats"""
    try:
        rider = Rider.objects.get(user=request.user)
        
        # Calculate date ranges
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Get completed orders - using 'delivered' status instead of completed_at
        completed_orders = Order.objects.filter(
            rider=rider,
            status='delivered'  # or whatever status value represents completed orders
        )
        
        # Calculate earnings for different periods using updated_at instead of completed_at
        today_orders = completed_orders.filter(
            updated_at__date=today
        )
        today_earnings = today_orders.aggregate(
            total=Coalesce(Sum('delivery_fee'), 0, output_field=FloatField())
        )['total']
        today_count = today_orders.count()
        
        week_orders = completed_orders.filter(
            updated_at__date__gte=week_start
        )
        week_earnings = week_orders.aggregate(
            total=Coalesce(Sum('delivery_fee'), 0, output_field=FloatField())
        )['total']
        week_count = week_orders.count()
        
        month_orders = completed_orders.filter(
            updated_at__date__gte=month_start
        )
        month_earnings = month_orders.aggregate(
            total=Coalesce(Sum('delivery_fee'), 0, output_field=FloatField())
        )['total']
        month_count = month_orders.count()
        
        total_earnings = completed_orders.aggregate(
            total=Coalesce(Sum('delivery_fee'), 0, output_field=FloatField())
        )['total']
        total_count = completed_orders.count()
        
        # Calculate delivery stats
        total_deliveries = total_count
        
        # Calculate total distance (if available)
        # If you don't store distance directly, we might need to skip this or calculate it
        total_distance = 0
        
        # Average rating (placeholder)
        avg_rating = 4.8
        
        # Calculate completion rate
        total_assigned = Order.objects.filter(
            rider=rider
        ).count()
        
        completion_rate = (total_deliveries / total_assigned * 100) if total_assigned > 0 else 0
        
        # Get recent earnings (last 10 completed orders)
        recent_earnings = []
        for order in completed_orders.order_by('-updated_at')[:10]:
            # Try to get distance info - adapt this to your model structure
            distance = 0
            if hasattr(order, 'pickup_latitude') and hasattr(order, 'pickup_longitude') and \
               hasattr(order, 'delivery_latitude') and hasattr(order, 'delivery_longitude'):
                if all([order.pickup_latitude, order.pickup_longitude, 
                         order.delivery_latitude, order.delivery_longitude]):
                    # Calculate distance if you have coordinates
                    try:
                        distance = calculate_distance(
                            float(order.pickup_latitude), float(order.pickup_longitude),
                            float(order.delivery_latitude), float(order.delivery_longitude)
                        )
                    except:
                        pass
            
            # Get customer name if available
            customer_name = order.customer_name if hasattr(order, 'customer_name') and order.customer_name else "Anonymous"
            
            recent_earnings.append({
                'date': order.updated_at,
                'order_number': order.order_number,
                'customer': customer_name,
                'distance': float(distance),
                'amount': float(order.delivery_fee) if order.delivery_fee else 0,
                'status': 'completed'
            })
        
        # Get penalties (placeholder - implement based on your penalty model)
        # Based on your model structure, you seem to have rider_penalties related to orders
        total_penalties = 0
        recent_penalties = []
        
        return JsonResponse({
            'success': True,
            'today': today_earnings,
            'today_orders': today_count,
            'week': week_earnings,
            'week_orders': week_count,
            'month': month_earnings,
            'month_orders': month_count,
            'total': total_earnings,
            'total_orders': total_count,
            'total_deliveries': total_deliveries,
            'total_distance': total_distance,
            'avg_rating': avg_rating,
            'completion_rate': completion_rate,
            'total_penalties': total_penalties,
            'recent_earnings': recent_earnings,
            'recent_penalties': recent_penalties
        })
    except Exception as e:
        logger.error(f"Error in rider earnings stats API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def rider_earnings_chart_api(request):
    """API endpoint for rider earnings chart data"""
    try:
        rider = Rider.objects.get(user=request.user)
        
        # Get period from request
        period = request.GET.get('period', 'week')
        
        # Calculate date range based on period
        today = timezone.now().date()
        
        if (period == 'week'):
            start_date = today - timedelta(days=6)  # Last 7 days
            date_format = '%a'  # Day name (Mon, Tue, etc.)
        elif (period == 'month'):
            start_date = today - timedelta(days=29)  # Last 30 days
            date_format = '%d %b'  # Day and month (15 Jan)
        else:  # year
            start_date = today.replace(month=1, day=1)  # Start of year
            date_format = '%b'  # Month name (Jan, Feb, etc.)
        
        # Get completed orders within date range - using updated_at instead of completed_at
        completed_orders = Order.objects.filter(
            rider=rider,
            status='delivered',  # or whatever status value represents completed orders
            updated_at__date__gte=start_date,
            updated_at__date__lte=today
        )
        
        # Group by date and calculate daily earnings
        from django.db.models.functions import TruncDate
        
        daily_earnings = completed_orders.annotate(
            date=TruncDate('updated_at')  # Use updated_at instead of completed_at
        ).values('date').annotate(
            total=Sum('delivery_fee')
        ).order_by('date')
        
        # Create date range and initialize earnings with zeros
        labels = []
        values = []
        
        current_date = start_date
        date_dict = {item['date']: float(item['total']) for item in daily_earnings}
        
        while current_date <= today:
            labels.append(current_date.strftime(date_format))
            values.append(date_dict.get(current_date, 0))
            current_date += timedelta(days=1)
        
        return JsonResponse({
            'success': True,
            'labels': labels,
            'values': values
        })
    except Exception as e:
        logger.error(f"Error in rider earnings chart API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
        
@login_required
def update_rider_profile(request):
    """Updates the rider profile."""
    if request.method == 'POST':
        try:
            rider = Rider.objects.get(user=request.user)
            
            data = request.POST
            # Print received data for debugging
            print(f"Received data: {data}")
            
            # Update user information
            if 'first_name' in data:
                rider.user.first_name = data.get('first_name')
            if 'last_name' in data:
                rider.user.last_name = data.get('last_name')
            if 'email' in data:
                rider.user.email = data.get('email')
            
            # Update rider-specific fields
            if 'phone_number' in data:
                rider.phone_number = data.get('phone_number')
            if 'address' in data:
                rider.address = data.get('address')
            
            # Handle password change
            if 'current_password' in data and 'new_password' in data:
                if not rider.user.check_password(data.get('current_password')):
                    return JsonResponse({'status': 'error', 'message': 'Current password is incorrect'}, status=400)
                rider.user.set_password(data.get('new_password'))
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, rider.user)
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                rider.profile_picture = request.FILES['profile_picture']
            
            # Save changes
            rider.user.save()
            rider.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Profile updated successfully',
                'user': {
                    'first_name': rider.user.first_name,
                    'last_name': rider.user.last_name,
                    'email': rider.user.email
                }
            })
        
        except Rider.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Rider profile not found'}, status=404)
        except Exception as e:
            import traceback
            print(f"Error updating profile: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'status': 'error', 'message': f'Error: {str(e)}'}, status=400)
    
    # If not POST method
    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

@login_required
def decline_order_api(request, order_id):
    """API endpoint for a rider to decline a gas delivery order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)
    
    try:
        rider = Rider.objects.get(user=request.user)
        from orders.models import Order, OrderRiderAction
        
        # Get the order
        order = get_object_or_404(Order, id=order_id)
        
        # Get rider location if available
        rider_lat = getattr(rider, 'latitude', None)
        rider_lng = getattr(rider, 'longitude', None)
        
        # Record the decline action
        OrderRiderAction.record_action(
            order=order,
            rider=rider,
            action_type='declined',
            notes="Rider declined gas delivery order",
            lat=rider_lat,
            lng=rider_lng
        )
        
        # Log the decline
        logger.info(f"Rider {rider.id} declined order {order.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'You have declined this order'
        })
        
    except Exception as e:
        logger.error(f"Error in decline order API: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def start_delivery_api(request, order_id):
    """API endpoint for riders to mark gas tank order as in-transit (collected from business)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'}, status=405)
    
    try:
        rider = Rider.objects.get(user=request.user)
        from orders.models import Order, OrderRiderAction
        
        # Get the order
        order = get_object_or_404(Order, id=order_id)
        
        # Check if the order is assigned to this rider
        from orders.models import OrderAssignmentGroup
        assignment_groups = OrderAssignmentGroup.objects.filter(
            riders=rider,
            order=order,
            is_active=True
        )
        
        if not assignment_groups.exists():
            return JsonResponse({
                'success': False, 
                'error': 'This gas delivery order is not assigned to you'
            })
        
        # Check if the order is in a valid state to start delivery
        if order.status not in ['ready', 'assigned', 'preparing']:
            return JsonResponse({
                'success': False, 
                'error': f'Cannot start delivery for order in {order.get_status_display()} status'
            })
        
        # Update the order status to in_transit
        order.status = 'in_transit'
        order.save()
        
        # Get rider location if available
        rider_lat = getattr(rider, 'latitude', None)
        rider_lng = getattr(rider, 'longitude', None)
        
        # Record the action
        OrderRiderAction.record_action(
            order=order,
            rider=rider,
            action_type='started',
            notes=f"Rider started delivery of gas tanks from business",
            lat=rider_lat,
            lng=rider_lng
        )
        
        # Log the action
        logger.info(f"Rider {rider.id} started delivery for order {order.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Gas delivery started successfully',
            'order_id': order.id,
            'status': order.status
        })
    
    except Exception as e:
        logger.error(f"Error in start delivery API: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def mark_order_in_transit(request, order_id):
    """View to mark an order as in transit by a rider"""
    if request.method == 'POST':
        try:
            # Get rider profile for the current user
            rider = Rider.objects.get(user=request.user)
            
            # Get the order and verify it's assigned to this rider
            order = Order.objects.get(id=order_id)
            
            # Verify the rider is assigned to this order
            if hasattr(order, 'rider') and order.rider and order.rider == rider:
                # Update the order status to in_transit if it's ready for pickup
                if order.status == 'ready_for_pickup':
                    order.status = 'in_transit'
                    order.save()
                    messages.success(request, f"Order #{order.id} is now in transit.")
                else:
                    messages.error(request, f"Cannot mark order #{order.id} as in transit. Order must be ready for pickup first.")
            else:
                messages.error(request, "You are not assigned to this order.")
                
        except Rider.DoesNotExist:
            messages.error(request, "Rider profile not found.")
        except Order.DoesNotExist:
            messages.error(request, f"Order #{order_id} not found.")
        except Exception as e:
            messages.error(request, f"Error updating order status: {str(e)}")
    
    return redirect('riders:dashboard')

@login_required
def mark_order_delivered(request, order_id):
    """View to mark an order as delivered by a rider"""
    if request.method == 'POST':
        try:
            # Get rider profile for the current user
            rider = Rider.objects.get(user=request.user)
            
            # Get the order and verify it's assigned to this rider
            order = Order.objects.get(id=order_id)
            
            # Verify the rider is assigned to this order
            if hasattr(order, 'rider') and order.rider and order.rider == rider:
                # Update the order status to delivered if it's in transit
                if order.status == 'in_transit':
                    order.status = 'delivered'
                    order.delivered_at = timezone.now()
                    order.save()
                    messages.success(request, f"Order #{order.id} has been delivered successfully.")
                else:
                    messages.error(request, f"Cannot mark order #{order.id} as delivered. Order must be in transit first.")
            else:
                messages.error(request, "You are not assigned to this order.")
                
        except Rider.DoesNotExist:
            messages.error(request, "Rider profile not found.")
        except Order.DoesNotExist:
            messages.error(request, f"Order #{order_id} not found.")
        except Exception as e:
            messages.error(request, f"Error updating order status: {str(e)}")
    
    return redirect('riders:dashboard')

@login_required
def accept_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        rider = request.user.rider

        # Check if order is available to accept
        if order.status != 'available':
            messages.error(request, 'This order is no longer available.')
            return redirect('riders:dashboard')

        # Assign rider and update status
        order.rider = rider
        order.status = 'processing'
        order.save()

        # Record the rider action
        OrderRiderAction.objects.create(
            order=order,
            rider=rider,
            action='accept',
            status='processing'
        )

        messages.success(request, f'Order #{order.order_number} has been accepted and is now processing.')
        return redirect('riders:dashboard')

    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('riders:dashboard')
    except Exception as e:
        messages.error(request, f'Error accepting order: {str(e)}')
        return redirect('riders:dashboard')

@login_required
def incoming_orders_api(request):
    """
    API endpoint for fetching incoming orders for a rider based on their location.
    """
    if not request.user.is_authenticated:
        logger.error("User not authenticated")
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    
    try:
        # Get the rider associated with this user
        try:
            rider = Rider.objects.get(user=request.user)
            logger.info(f"Found rider profile for user {request.user.id}")
        except Rider.DoesNotExist:
            # Handle case where user has no rider profile
            logger.error(f"No Rider profile found for user {request.user.id}")
            return JsonResponse({
                'error': 'No rider profile found for this user',
                'orders': []
            }, status=404)
        
        # Check if rider has coordinates
        rider_lat = rider.latitude
        rider_lng = rider.longitude
        rider_region = rider.region
        
        logger.info(f"Rider coordinates: lat={rider_lat}, lng={rider_lng}, region={rider_region}")
        
        if not rider_lat or not rider_lng:
            logger.warning(f"Rider {rider.id} has no location coordinates")
            return JsonResponse({
                'error': 'Rider location not available',
                'orders': []
            }, status=400)
        
        # DEBUG: Get ALL orders regardless of status to see what's available
        # Get all available orders in rider's region
        orders = Order.objects.filter(
            status__iregex=r'^(pending|available)$'  # Match both pending and available, case-insensitive
        ).order_by('-created_at')
        logger.info(f"Total eligible orders (pending/available): {orders.count()}")

        # Log the status distribution
        status_counts = {}
        for order in orders:
            status_lower = order.status.lower() if order.status else 'unknown'
            if status_lower in status_counts:
                status_counts[status_lower] += 1
            else:
                status_counts[status_lower] = 1
        
        logger.info(f"Order status distribution: {status_counts}")
        
        # Log how many would have matched the usual filter criteria
        exact_match_count = Order.objects.filter(
            status='available',
            business__region=rider.region
        ).count()
        
        logger.info(f"Orders matching exact criteria (available + region match): {exact_match_count}")
        
        # Initialize orders list
        orders_data = []

        # Process each order
        for order in orders:
            logger.info(f"Processing order {order.id} (status: {order.status}, business region: {order.business.region if order.business and hasattr(order.business, 'region') else 'unknown'})")
            
            # Function to check if coordinate is valid
            def is_valid_coordinate(coord):
                if coord is None:
                    return False
                try:
                    float_val = float(coord)
                    return float_val != 0
                except (ValueError, TypeError):
                    return False
            
            # Get delivery coordinates with fallback to business coordinates
            delivery_lat = order.delivery_latitude
            delivery_lng = order.delivery_longitude
            
            # Check if we need to use business coordinates as fallback
            if not is_valid_coordinate(delivery_lat) or not is_valid_coordinate(delivery_lng):
                if order.business and is_valid_coordinate(order.business.latitude) and is_valid_coordinate(order.business.longitude):
                    delivery_lat = order.business.latitude
                    delivery_lng = order.business.longitude
                    logger.info(f"Using business coordinates as fallback for order {order.id}: {delivery_lat}, {delivery_lng}")
            
            # Final check if we have valid coordinates to display
            has_valid_coords = is_valid_coordinate(delivery_lat) and is_valid_coordinate(delivery_lng)
            display_coords = f"{delivery_lat}, {delivery_lng}" if has_valid_coords else "No coordinates available"
            logger.info(f"Order {order.id} coordinates: {display_coords}")

            try:
                # Calculate distance if we have coordinates
                distance = None
                if is_valid_coordinate(rider_lat) and is_valid_coordinate(rider_lng) and has_valid_coords:
                    distance = calculate_distance(
                        float(rider_lat), float(rider_lng),
                        float(delivery_lat), float(delivery_lng)
                    )
                    logger.info(f"Distance for order {order.id}: {distance:.2f} km")
                
                # Create order dictionary
                order_dict = {
                    'id': order.id,
                    'order_number': order.order_number,
                    'display_id': order.get_display_id(),
                    'pickup_location': order.business.name if order.business else "Unknown business",
                    'pickup_address': order.business.address if order.business and order.business.address else "No address available",
                    'pickup_latitude': str(delivery_lat) if has_valid_coords else None,
                    'pickup_longitude': str(delivery_lng) if has_valid_coords else None,
                    'dropoff_location': display_coords,
                    'region': order.business.region if order.business and hasattr(order.business, 'region') else None,
                    'distance': f"{distance:.1f} km" if distance is not None else "Unknown",
                    'created_at': order.created_at.strftime("%b %d, %I:%M %p"),
                    'status': order.status,  # Added status for debugging
                }
                
                orders_data.append(order_dict)
                logger.info(f"Added order {order.id} to response")
                
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
                continue
        
        logger.info(f"Total orders in response: {len(orders_data)}")
        return JsonResponse({'orders': orders_data})
        
    except Exception as e:
        logger.error(f"Error in incoming orders API: {str(e)}")
        return JsonResponse({
            'error': f'Error processing request: {str(e)}',
            'orders': []
        }, status=500)

@login_required
def far_orders_view(request):
    """View for orders that are farther than 300m from the rider but still in the same region"""
    if not request.user.is_authenticated:
        return redirect('riders:login')
    
    try:
        rider = Rider.objects.get(user=request.user)
        rider_region = rider.region if hasattr(rider, 'region') else None
        logger.info(f"Far orders view for rider {rider.id} in region {rider_region}")
        
        from orders.models import Order, OrderAssignmentGroup
        from django.db.models import Q
        
        # Get all available orders not assigned to this rider
        available_orders = Order.objects.filter(
            Q(status__iexact='available') | Q(status__iexact='pending')
        ).exclude(
            rider__isnull=False  #Exclude orders that already have a rider
        ).order_by('-created_at')
        
        # Function to check if coordinate is valid
        def is_valid_coordinate(coord):
            if coord is None:
                return False
            try:
                float_val = float(coord)
                return float_val != 0
            except (ValueError, TypeError):
                return False
        
        # Get rider coordinates
        rider_lat = rider.latitude
        rider_lng = rider.longitude
        rider_region = rider.region if hasattr(rider, 'region') else None
        
        # Prepare list for orders - ONLY same region orders beyond 300m
        same_region_far_orders = [] 
        
        for order in available_orders:
            try:
                business_region = order.business.region if order.business and hasattr(order.business, 'region') else "Unknown"
                order.region = business_region
                
                # Only consider orders in the same region as the rider OR orders without region
                if not (rider_region and business_region and rider_region == business_region):
                    logger.info(f"Skipping order #{order.id} - different region ({business_region} vs {rider_region})")
                    continue
                
                # For orders in same region or unknown region, check distance
                pickup_lat = order.pickup_latitude
                pickup_lng = order.pickup_longitude
                
                # If no pickup coordinates but we have business coordinates, use those
                if not is_valid_coordinate(pickup_lat) or not is_valid_coordinate(pickup_lng):
                    if order.business and is_valid_coordinate(order.business.latitude) and is_valid_coordinate(order.business.longitude):
                        pickup_lat = order.business.latitude
                        pickup_lng = order.business.longitude
                        logger.info(f"Using business coordinates for order {order.id}: {pickup_lat}, {pickup_lng}")
                
                # Calculate distance if we have coordinates
                if is_valid_coordinate(rider_lat) and is_valid_coordinate(rider_lng) and is_valid_coordinate(pickup_lat) and is_valid_coordinate(pickup_lng):
                    distance = calculate_distance(
                        float(rider_lat), float(rider_lng),
                        float(pickup_lat), float(pickup_lng)
                    )
                    
                    # Format distance for display
                    order.distance = f"{distance:.1f} km"
                    logger.info(f"Order #{order.id} distance: {distance:.1f} km")
                    
                    # IMPORTANT: Categorization by distance
                    if distance > 0.3:  # Farther than 300m
                        same_region_far_orders.append(order)
                        logger.info(f"Order #{order.id} is in same region but far ({distance:.1f} km)")
                else:
                    # No valid coordinates for distance calculation
                    logger.warning(f"No valid coordinates for distance calculation for order #{order.id}")
                    same_region_far_orders.append(order)
                
                # Format the drop-off coordinates for display 
                delivery_lat = order.delivery_latitude
                delivery_lng = order.delivery_longitude
                
                # Check if we need to use business coordinates as fallback
                if not is_valid_coordinate(delivery_lat) or not is_valid_coordinate(delivery_lng):
                    if order.business and is_valid_coordinate(order.business.latitude) and is_valid_coordinate(order.business.longitude):
                        delivery_lat = order.business.latitude
                        delivery_lng = order.business.longitude
                
                # Set the dropoff_location attribute
                has_valid_coords = is_valid_coordinate(delivery_lat) and is_valid_coordinate(delivery_lng)
                order.dropoff_location = f"{delivery_lat}, {delivery_lng}" if has_valid_coords else "No coordinates available"
                
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
        
        logger.info(f"Found {len(same_region_far_orders)} orders in same region beyond 300m")
        return render(request, 'riders/far_orders.html', {'far_orders': same_region_far_orders})
    
    except Rider.DoesNotExist:
        return redirect('riders:login')
    except Exception as e:
        logger.error(f"Error showing far orders: {str(e)}")
        messages.error(request, f"Error retrieving orders: {str(e)}")
        return render(request, 'riders/far_orders.html', {'error': str(e)})

def assign_orders_to_riders():
    """
    Background function to assign orders to groups of riders based on proximity.
    This should be run on a scheduler or triggered when new orders come in.
    """
    try:
        from orders.models import Order, OrderAssignmentGroup
        import math
        
        # Function to calculate distance between two points
        def calculate_distance(lat1, lon1, lat2, lon2):
            """Calculate distance between two coordinates using Haversine formula."""
            # Convert to radians
            if not all([lat1, lon1, lat2, lon2]):
                return float('inf')  # Return infinity if any coordinate is missing
                
            lat1, lon1 = float(lat1), float(lon1)
            lat2, lon2 = float(lat2), float(lon2)
            
            # Radius of Earth in kilometers
            R = 6371.0
            
            # Convert latitude and longitude from degrees to radians
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # Difference in coordinates
            dlon = lon2_rad - lon1_rad
            dlat = lat2_rad - lat1_rad
            
            # Haversine formula
            a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c
            
            return distance
        
        # Get all unassigned orders that are not yet assigned to any rider
        # Include both 'available' and 'pending' status
        unassigned_orders = Order.objects.filter(
            status__in=['available', 'pending']
        ).exclude(
            id__in=OrderAssignmentGroup.objects.values_list('order_id', flat=True)
        )
        
        logger.info(f"Found {unassigned_orders.count()} unassigned orders with status 'available' or 'pending'")
        
        # Get all available riders
        available_riders = Rider.objects.filter(is_available=True)
        
        # Process each unassigned order
        for order in unassigned_orders:
            # Skip if order has no business location
            if not order.business or not order.business.latitude or not order.business.longitude:
                logger.warning(f"Order {order.id} has no valid business location, skipping assignment")
                continue
            
            # Get business coordinates
            business_lat = order.business.latitude
            business_lng = order.business.longitude
            
            # Calculate distance between order and each rider
            rider_distances = []
            for rider in available_riders:
                if rider.latitude and rider.longitude:
                    distance = calculate_distance(
                        business_lat, business_lng,
                        rider.latitude, rider.longitude
                    )
                    rider_distances.append((rider, distance))
            
            # Sort riders by distance to order
            rider_distances.sort(key=lambda x: x[1])
            
            # If there are at least 10 riders available
            if len(rider_distances) >= 10:
                closest_riders = [r[0] for r in rider_distances[:10]]
            else:
                # If fewer than 10 riders available, use all available riders
                closest_riders = [r[0] for r in rider_distances]
            
            # Skip if no riders available
            if not closest_riders:
                logger.warning(f"No riders available for order {order.id}, skipping assignment")
                continue
            
            # Create assignment group with 40-second timeout
            assignment_group = OrderAssignmentGroup.objects.create(
                order=order,
                expires_at=timezone.now() + timezone.timedelta(seconds=40)
            )
            
            # Add riders to assignment group
            for rider in closest_riders:
                assignment_group.riders.add(rider)
            
            logger.info(f"Created assignment group for order {order.id} with {len(closest_riders)} riders, expires in 40 seconds")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in assign_orders_to_riders: {str(e)}")
        return False



def manually_assign_orders(request):
    """
    Manual function to assign pending orders to riders based on proximity.
    This should be called from the admin interface or a management command.
    """
    try:
        from orders.models import Order, OrderAssignmentGroup
        from django.utils import timezone
        import math
        
        # Get all pending orders that are not yet assigned to any rider
        unassigned_orders = Order.objects.filter(
            status__in=['pending', 'confirmed', 'processing']
        ).exclude(
            id__in=OrderAssignmentGroup.objects.filter(is_active=True).values_list('order_id', flat=True)
        )
        
        logger.info(f"Found {unassigned_orders.count()} unassigned orders")
        
        # Get all available riders
        available_riders = Rider.objects.filter(is_available=True, latitude__isnull=False, longitude__isnull=False)
        logger.info(f"Found {available_riders.count()} available riders with location data")
        
        # Function to calculate distance between two points
        def calculate_distance(lat1, lon1, lat2, lon2):
            """Calculate distance between two coordinates using Haversine formula."""
            # Convert to radians
            if not all([lat1, lon1, lat2, lon2]):
                return float('inf')  # Return infinity if any coordinate is missing
                
            lat1, lon1 = float(lat1), float(lon1)
            lat2, lon2 = float(lat2), float(lon2)
            
            # Radius of Earth in kilometers
            R = 6371.0
            
            # Convert latitude and longitude from degrees to radians
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # Difference in coordinates
            dlon = lon2_rad - lon1_rad
            dlat = lat2_rad - lat1_rad
            
            # Haversine formula
            a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c
            
            return distance
        
        # Process each unassigned order
        assignments_created = 0
        for order in unassigned_orders:
            # Skip if order has no business location
            if not order.business or not order.business.latitude or not order.business.longitude:
                logger.warning(f"Order {order.id} has no valid business location, skipping assignment")
                continue
            
            # Get business coordinates
            business_lat = order.business.latitude
            business_lng = order.business.longitude
            
            # Calculate distance between order and each rider
            rider_distances = []
            for rider in available_riders:
                if rider.latitude and rider.longitude:
                    distance = calculate_distance(
                        business_lat, business_lng,
                        rider.latitude, rider.longitude
                    )
                    rider_distances.append((rider, distance))
            
            # Sort riders by distance to order
            rider_distances.sort(key=lambda x: x[1])
            
            # Select riders within 300m (0.3km)
            nearby_riders = [(rider, dist) for rider, dist in rider_distances if dist <= 0.3]
            logger.info(f"Order {order.id} has {len(nearby_riders)} riders within 300m")
            
            # If there are nearby riders, create an assignment group
            if nearby_riders:
                # Create assignment group with 40-second timeout
                assignment_group = OrderAssignmentGroup.objects.create(
                    order=order,
                    is_active=True,
                    expires_at=timezone.now() + timezone.timedelta(seconds=40)
                )
                
                # Add riders to assignment group
                for rider, distance in nearby_riders:
                    assignment_group.riders.add(rider)
                    logger.info(f"Added rider {rider.id} at {distance:.2f}km to assignment group for order {order.id}")
                
                assignments_created += 1
                logger.info(f"Created assignment group for order {order.id} with {len(nearby_riders)} riders")
            else:
                # If no nearby riders, find the closest 5 riders regardless of distance
                closest_riders = rider_distances[:5] if rider_distances else []
                if closest_riders:
                    # Create assignment group with 40-second timeout
                    assignment_group = OrderAssignmentGroup.objects.create(
                        order=order,
                        is_active=True,
                        expires_at=timezone.now() + timezone.timedelta(seconds=40)
                    )
                    
                    # Add riders to assignment group
                    for rider, distance in closest_riders:
                        assignment_group.riders.add(rider)
                        logger.info(f"Added rider {rider.id} at {distance:.2f}km to assignment group for order {order.id}")
                    
                    assignments_created += 1
                    logger.info(f"Created assignment group for order {order.id} with {len(closest_riders)} riders (no nearby riders found)")
        
        return JsonResponse({
            'success': True,
            'message': f"Created {assignments_created} assignment groups",
            'unassigned_orders': unassigned_orders.count(),
            'available_riders': available_riders.count(),
            'assignments_created': assignments_created
        })
    
    except Exception as e:
        logger.error(f"Error in manually_assign_orders: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['GET'])
def get_areas(request):
    """Fetch areas based on the selected region"""
    region = request.GET.get('region')
    if not region:
        return JsonResponse({'error': 'Region parameter is required'}, status=400)
    
    try:
        # Import necessary models
        from operations.models import Area
        
        # Query areas by region
        areas = Area.objects.filter(region=region).values('id', 'name')
        
        # Return the areas as JSON
        return JsonResponse({'areas': list(areas)})
    
    except Exception as e:
        logger.error(f"Error fetching areas: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

# Password reset views
@csrf_exempt
def forgot_password(request):
    """Handle forgot password requests"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number', '').strip()
            
            # Validate phone number
            if not phone_number:
                return JsonResponse({"error": "Phone number is required"}, status=400)
            
            # Normalize phone number if needed
            normalized_phone = normalize_phone(phone_number)
            
            # Check if user exists
            try:
                user = CustomUser.objects.get(phone=normalized_phone)
            except CustomUser.DoesNotExist:
                return JsonResponse({"error": "No account found with this phone number"}, status=404)
            
            # Check if user is a rider
            try:
                rider = Rider.objects.get(user=user)
            except Rider.DoesNotExist:
                return JsonResponse({"error": "This phone number is not associated with a rider account"}, status=404)
            
            # Generate OTP
            otp = str(random.randint(10000, 99999))
            expiry_time = timezone.now() + timedelta(minutes=10)  # 10 minutes expiry
            
            # Save OTP
            otp_record, created = OTPCredit.objects.update_or_create(
                user=user,
                defaults={
                    "otp": otp,
                    "otp_timestamp": timezone.now(),
                    "otp_expiry": expiry_time
                }
            )
            
            # Send OTP via SMS
            otp_sent = send_otp_via_sms(normalized_phone, otp)
            if not otp_sent:
                return JsonResponse({"error": "Failed to send OTP. Please try again."}, status=500)
            
            # Store phone number in session for use in subsequent requests
            request.session['reset_phone_number'] = normalized_phone
            
            return JsonResponse({
                "success": True,
                "message": "OTP sent successfully",
                "phone_number": normalized_phone
            })
                
        except Exception as e:
            logger.error(f"Error in forgot_password: {str(e)}")
            return JsonResponse({"error": "An error occurred. Please try again."}, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def reset_password_verify(request):
    """Render the OTP verification page for password reset"""
    if request.method == "GET":
        phone_number = request.session.get('reset_phone_number', '')
        return render(request, "riders/reset_password_verify.html", {"phone": phone_number})
    
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def verify_reset_otp(request):
    """Verify the OTP for password reset"""
    if request.method == "POST":
        try:
            # Handle both JSON and form data requests
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                    otp = data.get('otp', '')
                    phone_number = data.get('phone_number', '')
                except json.JSONDecodeError:
                    return JsonResponse({"error": "Invalid JSON data"}, status=400)
            else:
                otp = request.POST.get('otp', '')
                phone_number = request.POST.get('phone_number', '')

            # Ensure we have valid data
            if not otp:
                return JsonResponse({"error": "OTP is required"}, status=400)

            if not phone_number:
                phone_number = request.session.get('reset_phone_number', '')

            if not phone_number:
                return JsonResponse({"error": "Phone number is required"}, status=400)

            normalized_phone = normalize_phone(phone_number)

            try:
                user = CustomUser.objects.get(phone=normalized_phone)
                otp_record = OTPCredit.objects.filter(user=user).order_by('-otp_timestamp').first()

                if not otp_record:
                    return JsonResponse({"error": "OTP not found. Please request a new one."}, status=400)

                current_time = timezone.now()
                if current_time > otp_record.otp_expiry:
                    return JsonResponse({"error": "OTP has expired. Please request a new one."}, status=400)

                if str(otp_record.otp) != str(otp):
                    return JsonResponse({"error": "Invalid OTP. Please try again."}, status=400)

                # OTP is verified - store verification in session
                request.session['otp_verified'] = True
                request.session['reset_user_id'] = user.id

                return JsonResponse({"success": True, "message": "OTP verified successfully"})

            except CustomUser.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

        except Exception as e:
            logger.error(f"Error in verify_reset_otp: {str(e)}")
            return JsonResponse({"error": "An error occurred. Please try again."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def resend_reset_otp(request):
    """Resend OTP for password reset"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number', '').strip()

            if not phone_number:
                phone_number = request.session.get('reset_phone_number', '')

            if not phone_number:
                return JsonResponse({"error": "Phone number is required"}, status=400)

            normalized_phone = normalize_phone(phone_number)

            try:
                user = CustomUser.objects.get(phone=normalized_phone)
                otp_record = OTPCredit.objects.filter(user=user).order_by('-otp_timestamp').first()

                # Check if we can send a new OTP (prevent spamming)
                if otp_record and (timezone.now() - otp_record.otp_timestamp).seconds < 60:
                    return JsonResponse({"error": "Please wait 60 seconds before requesting a new OTP."}, status=400)

                # Generate new OTP
                otp = str(random.randint(10000, 99999))
                expiry_time = timezone.now() + timedelta(minutes=10)

                # Save OTP
                otp_record, created = OTPCredit.objects.update_or_create(
                    user=user,
                    defaults={
                        "otp": otp,
                        "otp_timestamp": timezone.now(),
                        "otp_expiry": expiry_time
                    }
                )

                # Send OTP via SMS
                otp_sent = send_otp_via_sms(normalized_phone, otp)
                if not otp_sent:
                    return JsonResponse({"error": "Failed to send OTP. Please try again."}, status=500)

                return JsonResponse({"success": True, "message": "OTP resent successfully"})

            except CustomUser.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

        except Exception as e:
            logger.error(f"Error in resend_reset_otp: {str(e)}")
            return JsonResponse({"error": "An error occurred. Please try again."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def reset_password(request):
    """Reset user password after OTP verification"""
    if request.method == "POST":
        try:
            # Handle both JSON and form data requests
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                    new_password = data.get('new_password', '')
                    phone_number = data.get('phone_number', '')
                except json.JSONDecodeError:
                    return JsonResponse({"error": "Invalid JSON data"}, status=400)
            else:
                new_password = request.POST.get('new_password', '')
                phone_number = request.POST.get('phone_number', '')

            # Validate required fields
            if not new_password:
                return JsonResponse({"error": "New password is required"}, status=400)

            if not phone_number:
                phone_number = request.session.get('reset_phone_number', '')

            if not phone_number:
                return JsonResponse({"error": "Phone number is required"}, status=400)

            # Check if OTP was verified
            otp_verified = request.session.get('otp_verified', False)
            reset_user_id = request.session.get('reset_user_id')

            if not otp_verified:
                return JsonResponse({"error": "OTP verification required before resetting password"}, status=400)

            normalized_phone = normalize_phone(phone_number)

            try:
                user = CustomUser.objects.get(phone=normalized_phone)

                # Extra security check - ensure user_id matches the one from OTP verification
                if reset_user_id != user.id:
                    return JsonResponse({"error": "Unauthorized password reset attempt"}, status=403)

                # Update password
                user.password = make_password(new_password)
                user.save()

                # Clear the OTP record
                OTPCredit.objects.filter(user=user).delete()

                # Clear session data
                request.session.pop('otp_verified', None)
                request.session.pop('reset_user_id', None)
                request.session.pop('reset_phone_number', None)

                return JsonResponse({"success": True, "message": "Password reset successfully"})

            except CustomUser.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

        except Exception as e:
            logger.error(f"Error in reset_password: {str(e)}")
            return JsonResponse({"error": "An error occurred. Please try again."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_update_location(request):
    """API View for updating rider location with address information."""
    try:
        rider = Rider.objects.get(user=request.user)
        
        # Extract location data
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        is_online = request.data.get('is_online', True)  # Default to True if not provided
        address = request.data.get('address')  # Get address from request if available
        
        # Log received data
        logger.info(f"Rider location update received - Lat: {latitude}, Lng: {longitude}, Online: {is_online}, Address: {address}")
        
        # Update rider location
        rider.latitude = latitude
        rider.longitude = longitude
        rider.is_available = is_online
        
        # If address was provided, update it
        if address:
            rider.address = address
            logger.info(f"Updated rider address to: {address}")
        
        rider.last_location_update = timezone.now()
        rider.save()
        
        return Response({
            'status': 'success',
            'latitude': latitude,
            'longitude': longitude,
            'is_online': is_online,
            'address': address if address else None
        })
    except Rider.DoesNotExist:
        return Response({'status': 'error', 'message': 'Rider not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating rider location: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)
