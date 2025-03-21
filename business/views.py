import json
import random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from orders.models import Order
from user_verification.utils import create_otp_for_user, send_otp_via_sms
from .models import Business, BusinessProfile, Product, Category
from .serializers import BusinessSerializer
from operations.models import CustomUser, OTPCredit, UserProfile
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import ProductForm
from .utils import check_low_stock
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse, reverse_lazy

# Create your views here.

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated]
    
    




@csrf_exempt
def business_register(request):
    """Handles Business Registration"""
    if request.method == "GET":
        return render(request, "business/register.html")

    if request.method == 'POST':
        try:
            print(" Raw Request Body:", request.body)
            
            # Check if the request is JSON or form data
            if request.content_type and 'application/json' in request.content_type:
                # Handle JSON data
                data = json.loads(request.body)
            else:
                # Handle form data
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

            # Validate required fields
            if not all([phone, business_name, owner_name, password, region]):
                return JsonResponse({'error': 'All fields are required'}, status=400)

            if password != confirm_password and confirm_password:  # Only check if confirm_password was provided
                return JsonResponse({'error': 'Passwords do not match'}, status=400)

            # Ensure phone format
            cleaned_phone = ''.join(filter(str.isdigit, phone))
            if not cleaned_phone.startswith('255'):
                if cleaned_phone.startswith('0'):
                    cleaned_phone = '255' + cleaned_phone[1:]
                elif cleaned_phone.startswith('7'):
                    cleaned_phone = '255' + cleaned_phone

            # Check if the phone number already exists
            if CustomUser.objects.filter(phone=cleaned_phone).exists():
                return JsonResponse({'error': 'Phone number already exists'}, status=400)

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

            # Create associated business with location data
            business = Business.objects.create(
                user=user, 
                name=business_name,
                owner_name=owner_name,
                phone=cleaned_phone,
                region=region,
                address=address,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None
            )

            # Create OTP record
            OTPCredit.objects.create(
                user=user,
                otp=otp,
                otp_expiry=otp_expiry
            )

            # Send OTP via SMS
            send_otp_via_sms(cleaned_phone, otp)

            # Include phone number in the redirect URL
            verification_url = f"{reverse('user_verification:verify_otp')}?phone={cleaned_phone}"
            
            return JsonResponse({
                'message': 'Registration successful! Please verify your phone number.',
                'phone': cleaned_phone,
                'redirect_url': verification_url,
                'otp_age': (otp_expiry - timezone.now()).seconds if otp_expiry else None
            })

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

def add_product(request):
    """View to add a new product"""
    # Debug information about the current user
    print(f"User ID: {request.user.id}")
    print(f"User Role: {request.user.role}")
    print(f"User Phone: {request.user.phone}")
    
    # Use the related_name from the model to access businesses
    try:
        business = request.user.businesses.first()
        if business:
            print(f"Found business: {business.name} (ID: {business.id}) for user {request.user.phone}")
        else:
            print(f"No business found for user {request.user.phone}")
    except Exception as e:
        print(f"Error retrieving business: {str(e)}")
        business = None
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # Associate the product with the current business
            product = form.save(commit=False)
            
            # Get the business associated with the current user
            try:
                # Use the related_name from the model to access businesses
                business = request.user.businesses.first()
                
                if business:
                    print(f"Found business: {business.name} (ID: {business.id})")
                    product.business = business
                    product.save()
                    messages.success(request, "Product added successfully!")
                    return redirect('business:business_dashboard')
                else:
                    # If no business exists, create one for this user
                    print("No business found, creating one")
                    new_business = Business.objects.create(
                        user=request.user,
                        name=f"{request.user.first_name}'s Business",
                        owner_name=request.user.first_name or "Business Owner",
                        phone=request.user.phone,
                        region=request.user.region
                    )
                    product.business = new_business
                    product.save()
                    messages.success(request, "New business created and product added successfully!")
                    return redirect('business:business_dashboard')
            except Exception as e:
                print(f"Error in add_product: {str(e)}")
                messages.error(request, f"Error saving product: {str(e)}")
        else:
            print(f"Form errors: {form.errors}")
            messages.error(request, "There was an error with your submission. Please check the form.")
    else:
        form = ProductForm()
    
    # Get all categories for the dropdown
    categories = Category.objects.all().order_by('name')
    
    return render(request, 'business/add_product.html', {
        'form': form,
        'categories': categories
    })


@login_required
def sales_history(request):
    """View for displaying sales history"""
    orders = Order.objects.filter(business=request.user.businesses.first()).order_by('-created_at')
    return render(request, 'business/sales_history.html', {'orders': orders})

@login_required
def earnings(request):
    """View for displaying earnings"""
    total_earnings = Order.objects.filter(business=request.user.businesses.first(), status='completed').aggregate(total=models.Sum('total_price'))['total'] or 0
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