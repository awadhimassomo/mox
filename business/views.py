import json
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db.models import Sum, Q
from orders.models import Order
from user_verification.utils import create_otp_for_user, send_otp_via_sms
from .models import Business, BusinessProfile, Product, Category
from .serializers import BusinessSerializer, ProductSerializer, CategorySerializer
from operations.models import CustomUser, OTPCredit, UserProfile
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import ProductForm
from .utils import check_low_stock
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse, reverse_lazy
from io import BytesIO
import pandas as pd
from django.http import HttpResponse
from datetime import datetime
from django.core.paginator import Paginator
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Create your views here.

from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.hashers import make_password

@csrf_protect
def forgot_password(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        if not phone or len(phone) != 9:
            return render(request, 'business/forgot_password.html', {'error': 'Enter a valid 9-digit phone number.'})
        phone_full = '+255' + phone
        try:
            user = CustomUser.objects.get(phone=phone_full)
        except CustomUser.DoesNotExist:
            return render(request, 'business/forgot_password.html', {'error': 'No account found with that phone number.'})
        # Create and send OTP
        otp = create_otp_for_user(user)
        send_otp_via_sms(user.phone, otp)
        request.session['reset_phone'] = user.phone
        request.session['reset_user_id'] = user.id
        return redirect('business:verify_reset_otp')
    return render(request, 'business/forgot_password.html')

@csrf_protect
def verify_reset_otp(request):
    phone = request.session.get('reset_phone')
    user_id = request.session.get('reset_user_id')
    if not phone or not user_id:
        return redirect('business:forgot_password')
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '').strip()
        try:
            user = CustomUser.objects.get(id=user_id, phone=phone)
        except CustomUser.DoesNotExist:
            return redirect('business:forgot_password')
        # Check OTP
        from user_verification.models import OTP
        try:
            otp_obj = OTP.objects.get(user=user, code=otp_input, is_used=False)
            if otp_obj.is_expired():
                return render(request, 'business/verify_otp_reset.html', {'error': 'OTP expired. Please request a new one.'})
            otp_obj.is_used = True
            otp_obj.save()
            request.session['reset_verified'] = True
            return redirect('business:reset_password')
        except OTP.DoesNotExist:
            return render(request, 'business/verify_otp_reset.html', {'error': 'Invalid OTP. Please try again.'})
    return render(request, 'business/verify_otp_reset.html')

@csrf_protect
def reset_password(request):
    phone = request.session.get('reset_phone')
    user_id = request.session.get('reset_user_id')
    verified = request.session.get('reset_verified')
    if not phone or not user_id or not verified:
        return redirect('business:forgot_password')
    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if not password1 or not password2:
            return render(request, 'business/reset_password.html', {'error': 'Please fill in both password fields.'})
        if password1 != password2:
            return render(request, 'business/reset_password.html', {'error': 'Passwords do not match.'})
        if len(password1) < 6:
            return render(request, 'business/reset_password.html', {'error': 'Password must be at least 6 characters.'})
        try:
            user = CustomUser.objects.get(id=user_id, phone=phone)
            user.password = make_password(password1)
            user.save()
            # Clear session for reset
            for key in ['reset_phone', 'reset_user_id', 'reset_verified']:
                if key in request.session:
                    del request.session[key]
            return redirect('business:business_login')
        except CustomUser.DoesNotExist:
            return redirect('business:forgot_password')
    return render(request, 'business/reset_password.html')

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing products.
    
    Provides CRUD operations for products associated with a business.
    Requires authentication for all operations.
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Allow read access to unauthenticated users
    queryset = Product.objects.all()  # Add default queryset
    
    @swagger_auto_schema(
        operation_summary="List products",
        operation_description="Returns a list of products, filtered by business_id if provided.",
        manual_parameters=[
            openapi.Parameter(
                'business_id',
                openapi.IN_QUERY,
                description="Filter products by business ID",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'category_id',
                openapi.IN_QUERY,
                description="Filter products by category ID",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'is_available',
                openapi.IN_QUERY,
                description="Filter products by availability",
                type=openapi.TYPE_BOOLEAN,
                required=False
            )
        ],
        responses={
            200: openapi.Response('OK', ProductSerializer(many=True)),
            401: 'Unauthorized'
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Create product",
        operation_description="Create a new product for the current user's business.",
        request_body=ProductSerializer,
        responses={
            201: openapi.Response('Created', ProductSerializer),
            400: 'Bad Request',
            401: 'Unauthorized'
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Retrieve product",
        operation_description="Retrieve details of a specific product by ID.",
        responses={
            200: openapi.Response('OK', ProductSerializer),
            401: 'Unauthorized',
            404: 'Not Found'
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        """
        Return products based on query parameters or user authentication.
        """
        queryset = Product.objects.all().filter(is_active=True)
        
        # Apply business_id filter if provided
        business_id = self.request.query_params.get('business_id')
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        elif self.request.user.is_authenticated:
            # Filter by current user's business if authenticated and no business_id provided
            try:
                business = Business.objects.get(user=self.request.user)
                queryset = queryset.filter(business=business)
            except Business.DoesNotExist:
                return Product.objects.none()
                
        # Apply category filter if provided
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # Apply availability filter if provided
        is_available = self.request.query_params.get('is_available')
        if is_available is not None:
            is_available_bool = is_available.lower() == 'true'
            queryset = queryset.filter(is_available=is_available_bool)
            
        return queryset

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product categories.
    
    Provides CRUD operations for categories associated with a business.
    Requires authentication for write operations, but allows read operations for all users.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @swagger_auto_schema(
        operation_summary="List categories",
        operation_description="Returns a list of categories for the current user's business if authenticated, or an empty list if not authenticated.",
        manual_parameters=[
            openapi.Parameter(
                'business_id',
                openapi.IN_QUERY,
                description="Filter categories by business ID",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            200: openapi.Response('OK', CategorySerializer(many=True)),
            401: 'Unauthorized'
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Create category",
        operation_description="Create a new category for the current user's business.",
        request_body=CategorySerializer,
        responses={
            201: openapi.Response('Created', CategorySerializer),
            400: 'Bad Request',
            401: 'Unauthorized'
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    def get_queryset(self):
        """Return only categories for the current user's business if authenticated"""
        print(f"\n\n[DEBUG] CategoryViewSet.get_queryset() called by user: {self.request.user}\n\n")
        
        # Check if business_id is provided in query parameters
        business_id = self.request.query_params.get('business_id')
        
        if business_id:
            # If business_id provided, filter by that business
            print(f"[DEBUG] Filtering by business_id: {business_id}")
            try:
                business = Business.objects.get(id=business_id)
                categories = Category.objects.filter(business=business, is_active=True)
                print(f"[DEBUG] Found {categories.count()} categories for business {business.name}")
                return categories
            except Business.DoesNotExist:
                print(f"[DEBUG] No business found with ID {business_id}")
                return Category.objects.none()
        elif self.request.user.is_authenticated:
            # Otherwise use the current user's business if authenticated
            print(f"[DEBUG] User is authenticated: {self.request.user.username}")
            try:
                business = Business.objects.get(user=self.request.user)
                print(f"[DEBUG] Found business: {business.name} (ID: {business.id})")
                categories = Category.objects.filter(business=business, is_active=True)
                print(f"[DEBUG] Found {categories.count()} categories for business {business.name}")
                return categories
            except Business.DoesNotExist:
                print(f"[DEBUG] No business found for user {self.request.user.username}")
                return Category.objects.none()
        else:
            print(f"[DEBUG] User is not authenticated")
        
        print("[DEBUG] Returning no categories")
        return Category.objects.none()  # No business, no categories



class BusinessRegistrationAPIView(APIView):
    """API endpoint for registering a new business."""
    permission_classes = []  # Public

    def post(self, request):
        data = request.data
        # Required fields
        phone = data.get('phone', '').strip()
        business_name = data.get('business_name', '').strip()
        owner_name = data.get('owner_name', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        region = data.get('region', '').strip()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        address = data.get('address', '').strip()
        email = data.get('email', '').strip() or None
        whatsapp = data.get('whatsapp', '').strip() or None

        # Validation
        if not phone or not business_name or not owner_name or not password or not confirm_password or not region:
            return Response({'error': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)
        if password != confirm_password:
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        from operations.models import CustomUser
        from .models import Business
        if CustomUser.objects.filter(phone=phone).exists():
            return Response({'error': 'Phone number already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = CustomUser.objects.create_user(phone=phone, password=password, email=email, whatsapp=whatsapp)
        # Create business
        business = Business.objects.create(
            user=user,
            name=business_name,
            owner_name=owner_name,
            address=address,
            region=region,
            latitude=latitude,
            longitude=longitude,
        )
        # Optionally: send OTP here if needed
        return Response({'success': True, 'business_id': business.id, 'user_id': user.id}, status=status.HTTP_201_CREATED)

    




def business_register(request):
    """Handles Business Registration"""
    if request.method == "GET":
        return render(request, "business/register.html")

    if request.method == 'POST':
        try:
            print(" Raw Request Body:", request.body)
            print(" Content-Type:", request.content_type)
            
            # Improved handling of different content types
            if request.content_type and 'application/json' in request.content_type:
                # Handle JSON data
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid JSON format'}, status=400)
            elif request.content_type and 'multipart/form-data' in request.content_type:
                # Handle multipart form data (file uploads)
                data = request.POST
            else:
                # Handle regular form data or any other content type
                data = request.POST
            
            # Extract required fields
            phone = data.get('phone', '').strip()
            business_name = data.get('business_name', '').strip()
            owner_name = data.get('owner_name', '').strip()
            password = data.get('password', '').strip()
            confirm_password = data.get('confirm_password', '').strip()
            region = data.get('region', '').strip()

            # Extract location data
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            address = data.get('address', '').strip()

            # Extract optional fields
            email = data.get('email', '').strip() or None
            whatsapp = data.get('whatsapp', '').strip() or None
            
            # Debug logging
            print("💬 Received fields:")
            print(" - phone:", phone)
            print(" - business_name:", business_name)
            print(" - owner_name:", owner_name)
            print(" - password:", "*" * len(password) if password else "<empty>")
            print(" - confirm_password:", "*" * len(confirm_password) if confirm_password else "<empty>")
            print(" - region:", region)
            print(" - address:", address)
            print(" - latitude:", latitude)
            print(" - longitude:", longitude)
            
            # Validate region specifically
            if not region or region == "":
                if request.content_type and 'application/json' in request.content_type:
                    return JsonResponse({'error': 'Please select a valid region'}, status=400)
                else:
                    messages.error(request, 'Please select a valid region')
                    return render(request, "business/register.html", {
                        'form_data': data,
                        'error': 'Please select a valid region'
                    })
                
            # Validate required fields
            if not all([phone, business_name, owner_name, password]):
                missing_fields = []
                if not phone: missing_fields.append('phone number')
                if not business_name: missing_fields.append('business name')
                if not owner_name: missing_fields.append('owner name')
                if not password: missing_fields.append('password')
                
                error_msg = f"Please fill in the following required fields: {', '.join(missing_fields)}"
                
                if request.content_type and 'application/json' in request.content_type:
                    return JsonResponse({'error': error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return render(request, "business/register.html", {
                        'form_data': data,
                        'error': error_msg
                    })

            # Only check password match if confirm_password field is explicitly provided
            # This makes confirm_password optional which helps with different form submissions
            if confirm_password and password != confirm_password:
                error_msg = 'Passwords do not match'
                print(f"Error: {error_msg}")
                if request.content_type and 'application/json' in request.content_type:
                    return JsonResponse({'error': error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return render(request, "business/register.html", {
                        'form_data': data,
                        'error': error_msg
                    })
                    
            # Password validation rules
            if len(password) < 8:
                error_msg = 'Password must be at least 8 characters long'
                print(f"Error: {error_msg}")
                if request.content_type and 'application/json' in request.content_type:
                    return JsonResponse({'error': error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return render(request, "business/register.html", {
                        'form_data': data,
                        'error': error_msg
                    })

            # Ensure phone format
            cleaned_phone = ''.join(filter(str.isdigit, phone))
            print(f"Original phone: {phone}, Cleaned phone: {cleaned_phone}")
            
            if not cleaned_phone.startswith('255'):
                if cleaned_phone.startswith('0'):
                    cleaned_phone = '255' + cleaned_phone[1:]
                elif cleaned_phone.startswith('7'):
                    cleaned_phone = '255' + cleaned_phone
                print(f"Reformatted phone: {cleaned_phone}")

            # Check if the phone number already exists
            existing_user = CustomUser.objects.filter(phone=cleaned_phone).first()
            if existing_user:
                error_msg = f"Phone number +{cleaned_phone} is already registered"
                print(f"Error: {error_msg} for user: {existing_user.first_name} (ID: {existing_user.id})")
                
                if request.content_type and 'application/json' in request.content_type:
                    return JsonResponse({'error': error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return render(request, "business/register.html", {
                        'form_data': data,
                        'error': error_msg
                    })

            # Generate OTP
            otp = random.randint(100000, 999999)
            otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
            print(f" Generated OTP: {otp} (expires in 5 minutes)")

            # Create user (inactive until OTP is verified)
            user = CustomUser.objects.create_user(
                phone=cleaned_phone, 
                email=email, 
                first_name=owner_name,
                password=password, 
                region=region,
                role="business_owner",
                is_active=False  # Requires OTP verification
            )
            
            # Generate and save OTP for user's verification
            # The create_otp_for_user function generates the OTP internally
            sent = create_otp_for_user(user=user)
            
            if sent:
                print(f"OTP generated and sent to {user.phone}")
            else:
                print(f"Failed to send OTP to {user.phone}")

            # Instead of continuing with business creation, redirect to OTP verification
            if request.content_type and 'application/json' in request.content_type:
                return JsonResponse({
                    'success': True,
                    'message': 'OTP sent for verification',
                    'redirect_url': f'/business/verify-otp/{user.id}/'
                })
            else:
                # For form submissions, redirect to OTP verification page
                return redirect('business:verify_otp', user_id=user.id)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"❌ Error in business registration: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def business_login(request):
    """Handles Business Owner Login"""
    if request.method == "GET":
        return render(request, "business/login.html")
        
    if request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            phone = data.get('phone', '').strip()
            password = data.get('password', '').strip()
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if not phone or not password:
                return JsonResponse({'error': 'Phone and password are required'}, status=400)

            # Clean phone number
            cleaned_phone = ''.join(filter(str.isdigit, phone))
            if not cleaned_phone.startswith('255'):
                if cleaned_phone.startswith('0'):
                    cleaned_phone = '255' + cleaned_phone[1:]
                elif cleaned_phone.startswith('7'):
                    cleaned_phone = '255' + cleaned_phone

            # Authenticate user
            user = authenticate(request, phone=cleaned_phone, password=password)
            
            if user is not None and user.is_active:
                if user.role != 'business_owner':
                    return JsonResponse({'error': 'Invalid account type'}, status=403)
                
                login(request, user)
                
                # Update business location if provided
                try:
                    business = Business.objects.get(user=user)
                    if latitude and longitude:
                        business.latitude = float(latitude)
                        business.longitude = float(longitude)
                        business.save()
                except Business.DoesNotExist:
                    pass  # Handle case where business doesn't exist
                
                return JsonResponse({
                    'message': 'Login successful',
                    'redirect': reverse('business:business_dashboard')
                })
            else:
                return JsonResponse({'error': 'Invalid credentials'}, status=401)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"❌ Error in business login: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)



@login_required
def business_list(request):
    """View for listing all businesses"""
    businesses = Business.objects.all()
    return render(request, 'business/businesses.html', {'businesses': businesses})

@login_required
def get_businesses_data(request):
    """API endpoint to fetch businesses data"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        businesses = Business.objects.filter(region=user_profile.region)
        
        data = []
        for business in businesses:
            orders_today = Order.objects.filter(
                business=business,
                created_at__date=timezone.now().date()
            ).count()
            
            data.append({
                'id': business.id,
                'name': business.name,
                'owner_name': business.owner_name,
                'phone': business.phone,
                'location': business.location,
                'region': business.get_region_display(),
                'orders_today': orders_today,
                'latitude': business.latitude,
                'longitude': business.longitude
            })
        
        return JsonResponse({
            'success': True,
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)




def business_dashboard(request):
    """View for the business dashboard"""
    # Get the business associated with the current user
    # Use the related_name from the model - user.businesses
    try:
        # This is the correct way to access the business since it's a ForeignKey with related_name="businesses"
        business = request.user.businesses.first()
        
        if business:
            print(f"Found business: {business.name} (ID: {business.id}) for user {request.user.phone}")
            # Only show products belonging to this business
            products = Product.objects.filter(business=business)
            print(f"Found {products.count()} products for business {business.name}")
        else:
            products = Product.objects.none()
            print(f"No business found for user {request.user.phone}")
    except Exception as e:
        print(f"Error retrieving business: {str(e)}")
        products = Product.objects.none()
        business = None
    
    # Get all categories for filter dropdown
    categories = Category.objects.all().order_by('name')
    
    # Get order data for this specific business
    total_sales = 0
    total_orders = 0
    if business:
        total_sales = Order.objects.filter(business=business, status='delivered').aggregate(total=Sum('total'))['total'] or 0
        total_orders = Order.objects.filter(business=business, status='delivered').count()
    
    # For orders tab - only get orders for this business
    incoming_orders = []
    processing_orders = []
    completed_orders = []
    if business:
        # Replace with case-insensitive queries filtered by the current business
        incoming_orders = Order.objects.filter(business=business, status__iexact='pending').order_by('-created_at')[:5]
        processing_orders = Order.objects.filter(
            business=business, 
            status__in=['processing', 'PROCESSING', 'ready_for_pickup', 'READY_FOR_PICKUP', 'in_transit', 'IN_TRANSIT']
        ).order_by('-created_at')[:10]
        completed_orders = Order.objects.filter(business=business, status__iexact='delivered').order_by('-created_at')[:5]
    
    # Check for low stock
    stock_alert = check_low_stock(products)
    
    return render(request, 'business/business_dashboard.html', {
        'products': products,
        'categories': categories,
        'total_sales': total_sales,
        'total_orders': total_orders,
        'stock_alert': stock_alert,
        'incoming_orders': incoming_orders,
        'processing_orders': processing_orders,
        'completed_orders': completed_orders,
        'business': business,  # Pass the business to the template
    })

@login_required
def add_product(request):
    """View to add a new product"""
    # Debug information about the current user
    print(f"User ID: {request.user.id}")
    print(f"User Role: {request.user.role}")
    print(f"User Phone: {request.user.phone}")
    
    user_business = None
    try:
        user_business = Business.objects.get(user=request.user)
    except Business.DoesNotExist:
        messages.error(request, "You do not have an associated business. Please create one to add products.")
        return redirect('business:create_business') # Or an appropriate page like 'business:business_dashboard'

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, business=user_business)
        if form.is_valid():
            product = form.save(commit=False)
            product.business = user_business
            # product.created_by = request.user # If you have such a field
            product.save()
            # form.save_m2m() # If your form has many-to-many fields
            messages.success(request, f"Product '{product.name}' added successfully!")
            return redirect('business:business_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(business=user_business)

    # Fetch categories for the current user's business
    categories_json_string = "[]"  # Default to an empty JSON array string
    categories_queryset = Category.objects.none()

    if user_business:
        try:
            categories_queryset = Category.objects.filter(business=user_business).select_related('parent').order_by('name')
            
            categories_list = []
            for cat in categories_queryset:
                categories_list.append({
                    'id': cat.id,
                    'name': cat.name,
                    'parent_id': cat.parent.id if cat.parent else None,
                    'category_type': getattr(cat, 'category_type', None), 
                    'is_top_level': getattr(cat, 'is_top_level', False) 
                })
            
            if categories_list:
                categories_json_string = json.dumps(categories_list)
            # messages.info(request, f"Loaded {len(categories_list)} categories for JS.") # Optional debug

        except AttributeError as ae:
            messages.warning(request, f"A category attribute might be missing: {str(ae)}. Categories might not display all info.")
            # categories_json_string will remain "[]" or be based on data successfully processed before error.
        except Exception as e:
            # import logging # Consider logging for server-side details
            # logger = logging.getLogger(__name__)
            # logger.error(f"Error fetching categories for business {user_business.id}: {e}", exc_info=True)
            messages.error(request, f"An error occurred while fetching categories: {str(e)}")
            # categories_json_string is already "[]" by default.

    context = {
        'form': form,
        'categories_for_js': categories_json_string,
        'categories_queryset': categories_queryset, 
        'business_name': user_business.name if user_business else "Your Business",
        'user_business': user_business  # Pass the actual business object
    }
    return render(request, 'business/add_product.html', context)

@csrf_exempt
def verify_otp(request, user_id):
    """Handle OTP verification for business registration"""
    # For GET requests, show the OTP verification page
    if request.method == "GET":
        return render(request, "business/otp_verification.html", {"user_id": user_id})
    
    # For POST requests, verify the OTP
    if request.method == "POST":
        try:
            # Get the user
            user = CustomUser.objects.get(id=user_id)
            
            # Get the OTP from form
            otp1 = request.POST.get('otp1', '')
            otp2 = request.POST.get('otp2', '')
            otp3 = request.POST.get('otp3', '')
            otp4 = request.POST.get('otp4', '')
            otp5 = request.POST.get('otp5', '')
            otp6 = request.POST.get('otp6', '')
            
            # Combine OTP digits
            submitted_otp = f"{otp1}{otp2}{otp3}{otp4}{otp5}{otp6}"
            
            # Check if OTP is valid
            from user_verification.models import OTPVerification
            try:
                # Get the most recent non-used OTP for this user
                otp_obj = OTPVerification.objects.filter(user=user, is_used=False).order_by('-otp_timestamp').first()
                
                if not otp_obj:
                    return render(request, "business/otp_verification.html", {
                        "user_id": user_id,
                        "error": "OTP expired or not found. Please request a new one."
                    })
                
                # Verify OTP
                if otp_obj.otp == submitted_otp and not otp_obj.is_expired():
                    # Mark OTP as used
                    otp_obj.is_used = True
                    otp_obj.save()
                    
                    # Activate user
                    user.is_active = True
                    user.save()
                    
                    # Create business with saved data
                    try:
                        # Extract form data from registration
                        business_name = user.first_name.split()[0] + "'s Business" # Default business name
                        phone = user.phone
                        owner_name = user.first_name
                        region = user.region
                        
                        # Create business
                        business = Business.objects.create(
                            user=user,
                            name=business_name,
                            owner_name=owner_name,
                            phone=phone,
                            region=region
                        )
                        
                        # Log in the user
                        login(request, user)
                        
                        # Redirect to dashboard
                        return redirect('business:business_dashboard')
                    except Exception as e:
                        print(f"Error creating business: {str(e)}")
                        return render(request, "business/otp_verification.html", {
                            "user_id": user_id,
                            "error": "Error creating business. Please contact support."
                        })
                else:
                    # Invalid OTP
                    return render(request, "business/otp_verification.html", {
                        "user_id": user_id,
                        "error": "Invalid OTP or OTP expired. Please try again or request a new one."
                    })
            except Exception as e:
                print(f"Error verifying OTP: {str(e)}")
                return render(request, "business/otp_verification.html", {
                    "user_id": user_id,
                    "error": f"Error verifying OTP. Please try again or request a new one. ({str(e)})"
                })
        except CustomUser.DoesNotExist:
            return render(request, "business/otp_verification.html", {
                "error": "User not found. Please register again."
            })
    
    return render(request, "business/otp_verification.html", {"user_id": user_id})


@csrf_exempt
def resend_otp(request):
    """Resend OTP for business registration"""
    if request.method == "POST":
        try:
            if request.content_type and 'application/json' in request.content_type:
                # Handle JSON data
                try:
                    data = json.loads(request.body)
                    user_id = data.get('user_id')
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid JSON format'}, status=400)
            else:
                # Handle form data
                user_id = request.POST.get('user_id')
            
            if not user_id:
                return JsonResponse({'error': 'User ID is required'}, status=400)
            
            # Get the user
            user = CustomUser.objects.get(id=user_id)
            
            # Generate and send new OTP
            create_otp_for_user(user)
            return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
        
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def mark_order_ready(request):
    """View to mark an order as ready for pickup"""
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        try:
            # Try to get business directly by user first
            business = None
            try:
                # First try to get business from business profile if it exists
                business_profile = BusinessProfile.objects.get(user=request.user)
                business = business_profile.business
            except BusinessProfile.DoesNotExist:
                # If no profile exists, try to get business directly
                business = Business.objects.get(user=request.user)
            
            print(f"Found business: {business.name} (ID: {business.id}) for user {request.user.phone}")
            
            # Get the order and verify it belongs to this business
            order = Order.objects.get(id=order_id, business=business)
            
            # Update the order status to ready_for_pickup
            current_status = order.status
            print(f"DEBUG: Order #{order.id} current status: {current_status}")
            
            # Accept both uppercase and lowercase status values
            if current_status.lower() in ['processing', 'pending', 'confirmed', 'assigned']:
                order.status = 'ready_for_pickup'
                order.save()
                messages.success(request, f"Order #{order.id} marked as ready for pickup.")
                print(f"DEBUG: Order status updated to: {order.status}")
            else:
                messages.error(request, f"Cannot mark order #{order.id} as ready. Current status: {current_status}")
                print(f"DEBUG: Invalid status transition from {current_status} to ready_for_pickup")
                
        except Business.DoesNotExist:
            messages.error(request, "Business not found for this user.")
            print(f"DEBUG: Business not found for user {request.user.id}")
        except Order.DoesNotExist:
            messages.error(request, f"Order #{order_id} not found or doesn't belong to your business.")
            print(f"DEBUG: Order {order_id} not found or doesn't belong to business")
        except Exception as e:
            messages.error(request, f"Error updating order: {str(e)}")
            print(f"DEBUG: Exception in mark_order_ready: {str(e)}")
    
    return redirect('business:business_dashboard')


@login_required
def earnings(request):
    """View for displaying earnings"""
    from django.db.models import Sum
    business = request.user.businesses.first()
    total_earnings = 0
    
    if business:
        # Use 'total' field instead of 'total_price' since that's what's available in the Order model
        total_earnings = Order.objects.filter(
            business=business, 
            status='completed'
        ).aggregate(total=Sum('total'))['total'] or 0
    
    return render(request, 'business/earnings.html', {'total_earnings': total_earnings})

@login_required
def profile(request):
    """View for displaying business profile"""
    profile, created = Business.objects.get_or_create(user=request.user, defaults={'name': request.user.first_name})
    
    return render(request, 'business/profile.html', {'profile': profile})

@login_required
def business_profile(request):
    """View for displaying business profile details and handling image uploads"""
    # Try to get the business associated with the current user
    business = request.user.businesses.first()
    
    # Check if this is a POST request for image upload
    if request.method == 'POST' and request.FILES and business:
        if 'cover_image' in request.FILES:
            # Handle cover image upload
            business.cover_image = request.FILES['cover_image']
            business.save()
            messages.success(request, 'Profile image updated successfully')
            return redirect('business:profile')
        
        elif 'banner' in request.FILES:
            # Handle banner upload
            business.banner = request.FILES['banner']
            business.save()
            messages.success(request, 'Banner updated successfully')
            return redirect('business:profile')
    
    # Count products if business exists
    product_count = 0
    if business:
        # Count all products associated with the business
        product_count = Product.objects.filter(business=business).count()
    
    return render(request, 'business/profile.html', {
        'business': business,
        'product_count': product_count
    })

@login_required
def create_business(request):
    """View to create a new business for the current user"""
    if request.method == "POST":
        # Process the form data
        business_name = request.POST.get('business_name')
        owner_name = request.POST.get('owner_name')
        phone = request.POST.get('phone')
        region = request.POST.get('region')
        
        if not business_name:
            messages.error(request, "Business name is required.")
            return render(request, 'business/create_business.html', {'regions': REGION_CHOICES})
        
        # Create new business
        try:
            business = Business.objects.create(
                user=request.user,
                name=business_name,
                owner_name=owner_name or request.user.first_name,
                phone=phone or request.user.phone,
                region=region or request.user.region
            )
            messages.success(request, f"Business '{business.name}' created successfully!")
            return redirect('business:business_dashboard')
        except Exception as e:
            messages.error(request, f"Error creating business: {str(e)}")
    
    # Render the form for GET requests
    return render(request, 'business/create_business.html', {
        'regions': REGION_CHOICES,
    })


@login_required
def manage_categories(request):
    """View for listing all categories with option to add new ones"""
    try:
        current_business = Business.objects.get(user=request.user)
        categories = Category.objects.filter(business=current_business, is_active=True).order_by('name')
    except Business.DoesNotExist:
        messages.error(request, 'You need to create a business before managing categories')
        return redirect('business:create_business')
    
    return render(request, 'business/manage_categories.html', {
        'categories': categories,
        'category_types': Category.CATEGORY_TYPES
    })

@login_required
def add_category(request):
    """Direct server-side view for adding new categories without JavaScript"""
    # Get the current user's business
    try:
        current_business = Business.objects.get(user=request.user)
    except Business.DoesNotExist:
        messages.error(request, 'You need to create a business before adding categories')
        return redirect('business:create_business')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_type = request.POST.get('category_type')
        parent_id = request.POST.get('parent')
        is_top_level = request.POST.get('is_top_level') == 'on'
        
        # Validate required fields
        if not name:
            messages.error(request, 'Category name is required')
            return redirect('business:add_category')
        
        # Create new category
        try:
            category = Category()
            category.name = name
            category.description = description
            category.category_type = category_type
            category.business = current_business  # Associate with current business
            
            # Set parent if provided
            if parent_id and parent_id != '':
                try:
                    # Only allow parents from the same business
                    parent = Category.objects.get(pk=parent_id, business=current_business)
                    category.parent = parent
                    # Cannot be top-level if has parent
                    category.is_top_level = False
                except Category.DoesNotExist:
                    # Parent doesn't exist or doesn't belong to this business
                    messages.error(request, 'Selected parent category is invalid')
                    return redirect('business:add_category')
            else:
                # Can be top-level if no parent
                category.is_top_level = is_top_level
            
            # Generate a unique slug for the category
            from django.utils.text import slugify
            import random
            import string
            
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            
            # Keep checking until we find a unique slug for this business
            while Category.objects.filter(slug=slug, business=current_business).exists():
                # Add a random suffix to make the slug unique
                random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                slug = f"{base_slug}-{random_suffix}"
                counter += 1
                if counter > 10:  # Safety limit
                    break
            
            category.slug = slug
            category.save()
            
            messages.success(request, f'Category "{name}" added successfully')
            
            # Redirect based on where request came from
            next_url = request.POST.get('next', 'business:manage_categories')
            return redirect(next_url)
            
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
            return redirect('business:add_category')
    
    # GET request - show form
    # Only show categories for this business
    categories = Category.objects.filter(business=current_business, is_active=True).order_by('name')
    return render(request, 'business/add_category.html', {
        'categories': categories,
        'category_types': Category.CATEGORY_TYPES,
        'next': request.GET.get('next', 'business:manage_categories')
    })

from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse

@csrf_exempt
def public_add_category(request):
    """AJAX endpoint for adding categories via JavaScript"""
    # Debug information
    print(f"\n\n[AJAX_ADD_CATEGORY] Request received at {request.path}")
    print(f"[AJAX_ADD_CATEGORY] Request method: {request.method}")
    print(f"[AJAX_ADD_CATEGORY] User: {request.user} (Authenticated: {request.user.is_authenticated})")
    print(f"[AJAX_ADD_CATEGORY] Headers: {dict(request.headers)}")
    
    # Print request body
    try:
        if request.body:
            print(f"[AJAX_ADD_CATEGORY] Request body: {request.body.decode('utf-8')}")
        else:
            print("[AJAX_ADD_CATEGORY] Request body is empty")
    except Exception as e:
        print(f"[AJAX_ADD_CATEGORY] Error decoding request body: {str(e)}")
    
    # Skip AJAX check for now
    # if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    #     return JsonResponse({'error': 'Invalid request'}, status=400)
        
    # Only allow POST method
    if request.method != 'POST':
        print("[AJAX_ADD_CATEGORY] Method not allowed")
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Hard-code a business ID for testing if the user is not authenticated
    # Get the current user's business
    try:
        if request.user.is_authenticated:
            current_business = Business.objects.get(user=request.user)
            print(f"[AJAX_ADD_CATEGORY] Found business ID: {current_business.id}")
        else:
            # For testing, try to get any business
            print("[AJAX_ADD_CATEGORY] User not authenticated, using a test business")
            current_business = Business.objects.first()
            if current_business:
                print(f"[AJAX_ADD_CATEGORY] Using test business ID: {current_business.id}")
            else:
                print("[AJAX_ADD_CATEGORY] No businesses found in the database!")
                return JsonResponse({'error': 'No business found'}, status=404)
    except Business.DoesNotExist:
        print("[AJAX_ADD_CATEGORY] No business found for this user")
        return JsonResponse({'error': 'No business found'}, status=404)
    except Exception as e:
        print(f"[AJAX_ADD_CATEGORY] Error getting business: {str(e)}")
        return JsonResponse({'error': f'Error finding business: {str(e)}'}, status=500)
    
    # Get form data
    try:
        # Handle both JSON and form data
        if 'application/json' in request.headers.get('Content-Type', ''):
            import json
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description', '')
            category_type = data.get('category_type')
            is_top_level = data.get('is_top_level', False)
        else:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            category_type = request.POST.get('category_type')
            is_top_level = request.POST.get('is_top_level') == 'on'
        
        # Validate required fields
        if not name:
            return JsonResponse({'error': 'Category name is required'}, status=400)
        
        # Create new category
        category = Category()
        category.name = name
        category.description = description
        category.category_type = category_type or 'general'  # Default to general if not provided
        category.business = current_business  # Associate with current business
        category.is_top_level = is_top_level
        category.is_active = True
        
        # Generate a unique slug for the category
        from django.utils.text import slugify
        import random
        import string
        
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        
        # Keep checking until we find a unique slug for this business
        while Category.objects.filter(slug=slug, business=current_business).exists():
            # Add a random suffix to make the slug unique
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            slug = f"{base_slug}-{random_suffix}"
            counter += 1
            if counter > 10:  # Safety limit
                break
        
        category.slug = slug
        category.save()
        
        # Return the new category details
        return JsonResponse({
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'category_type': category.category_type,
            'is_top_level': category.is_top_level,
            'is_active': category.is_active
        })
            
    except Exception as e:
        import traceback
        print(f"Error in ajax_add_category: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Error creating category: {str(e)}'}, status=500)

@login_required
def sales_history(request):
    """View for displaying sales history"""
    business = request.user.businesses.first()
    orders = []
    
    if business:
        orders = Order.objects.filter(business=business).order_by('-created_at')
    
    return render(request, 'business/sales_history.html', {
        'orders': orders,
        'business': business
    })

@login_required
def export_sales_history_excel(request):
    """Export sales history to Excel"""
    business = request.user.businesses.first()
    if not business:
        messages.error(request, "No business found for your account.")
        return redirect('business:business_dashboard')
    
    # Get all orders for this business
    orders = Order.objects.filter(business=business).order_by('-created_at')
    
    # Apply filters if provided
    date_filter = request.GET.get('date_filter')
    status_filter = request.GET.get('status_filter')
    search_query = request.GET.get('search')
    
    if date_filter:
        today = timezone.now().date()
        if date_filter == 'today':
            orders = orders.filter(created_at__date=today)
        elif date_filter == 'week':
            start_of_week = today - timezone.timedelta(days=today.weekday())
            orders = orders.filter(created_at__date__gte=start_of_week)
        elif date_filter == 'month':
            orders = orders.filter(created_at__month=today.month, created_at__year=today.year)
    
    if status_filter and status_filter != 'all':
        orders = orders.filter(status__iexact=status_filter)
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query)
        )
    
    # Create DataFrame from orders
    data = []
    for order in orders:
        data.append({
            'Order Number': order.order_number,
            'Customer': order.customer_name if hasattr(order, 'customer_name') else (order.customer.name if order.customer else 'N/A'),
            'Date': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'Status': order.status,
            'Total Amount': order.total,
            'Delivery Address': order.delivery_address.address if hasattr(order, 'delivery_address') and order.delivery_address else 'N/A',
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sales History', index=False)
        
        # Auto-adjust columns width
        worksheet = writer.sheets['Sales History']
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = max_len
    
    # Create HTTP response with Excel file
    output.seek(0)
    filename = f"sales_history_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def import_sales_history_excel(request):
    """Import sales data from Excel"""
    if request.method != 'POST' or 'excel_file' not in request.FILES:
        messages.error(request, "No file uploaded")
        return redirect('business:sales_history')
    
    excel_file = request.FILES['excel_file']
    
    # Check file extension
    if not excel_file.name.endswith(('.xlsx', '.xls')):
        messages.error(request, "Unsupported file format. Please upload an Excel file (.xlsx, .xls)")
        return redirect('business:sales_history')
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        
        # Process the data (this is just a demonstration, you may want to customize this)
        # For safety, we're just displaying what was imported, not actually creating orders
        
        row_count = len(df)
        messages.success(request, f"Successfully processed {row_count} records from Excel file. View console for details.")
        
        # You could process the data here to create or update orders
        # But for now we'll just pass this as information
        print(f"Imported {row_count} records from Excel")
        print(df.head())
        
    except Exception as e:
        messages.error(request, f"Error processing Excel file: {str(e)}")
    
    return redirect('business:sales_history')