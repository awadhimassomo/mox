from django.db import connection
from django.contrib.auth.decorators import login_required 
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Q, Count, Avg
from django.utils import timezone
import json
import logging
import math
from decimal import Decimal
from itertools import groupby
from django.db.models.functions import Abs

from riders.models import Rider
from django.db.models import F, ExpressionWrapper, FloatField
from django.db.models.functions import Abs

from business.models import Business, Product, Category, REGION_CHOICES
from riders.utils import calculate_distance
from .models import CustomerProfile, DeliveryAddress, Cart, CartItem, Favorite
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import CustomerProfileSerializer, UserSerializer, CustomerLoginSerializer
from orders.models import Order, OrderAssignmentGroup, OrderItem, TransportMode
from .forms import CustomerProfileForm, DeliveryAddressForm, CustomerSignUpForm
from operations.models import CustomUser
from riders.models import Rider as RiderProfile

# Configure logger
logger = logging.getLogger(__name__)

# Add a console handler if not already configured
if not logger.handlers:
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.setLevel(logging.DEBUG)

class CustomerProfileViewSet(viewsets.ModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticated]

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class CustomerLoginAPIView(APIView):
    """
    API endpoint for customer login.
    Returns JWT tokens on successful authentication.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Customer Login",
        request_body=CustomerLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': UserSerializer()
                    }
                )
            ),
            400: 'Invalid data',
            401: 'Invalid credentials'
        }
    )
    def post(self, request, *args, **kwargs):
        logger.info("Login request received")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        
        try:
            serializer = CustomerLoginSerializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                logger.warning(f"Validation failed. Errors: {serializer.errors}")
                logger.warning(f"Input data: {request.data}")
                return Response(
                    {
                        'status': 'error',
                        'code': 'validation_error',
                        'message': 'Invalid input data',
                        'errors': serializer.errors,
                        'received_data': str(request.data)
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user = serializer.validated_data.get('user')
            if not user:
                logger.error("No user found in validated data")
                return Response(
                    {'error': 'Authentication failed'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Get user data
            user_data = UserSerializer(user, context={'request': request}).data
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            logger.info(f"User {user.phone} logged in successfully")
            
            return Response({
                'status': 'success',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in login: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 'error',
                    'code': 'server_error',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Utility functions for common operations

def get_or_create_customer_profile(request):
    """
    Get existing customer profile or create a new one if needed.
    Returns the CustomerProfile object.
    """
    if not hasattr(request.user, 'customer_profile'):
        # Try to get an existing profile first
        try:
            customer = CustomerProfile.objects.get(user=request.user)
        except CustomerProfile.DoesNotExist:
            # Create a customer profile for the user only if it doesn't exist
            customer = CustomerProfile.objects.create(
                user=request.user,
                phone_number=f"temp_{request.user.id}"  # Temporary phone number
            )
    else:
        customer = request.user.customer_profile
    
    return customer


def calculate_cart_totals(cart):
    """
    Calculate cart subtotal, count, and other totals.
    Returns tuple of (subtotal, cart_count)
    """
    cart_items = cart.items.all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    cart_count = sum(item.quantity for item in cart_items)
    return subtotal, cart_count


def calculate_delivery_fee(business, delivery_address, transport_mode=None):
    """
    Calculate delivery fee based on distance between business and delivery address.
    If transport_mode is provided, use its pricing model. Otherwise, use default rate.
    """
    # Ensure both business and delivery address have coordinates
    if not all([business.latitude, business.longitude, delivery_address.latitude, delivery_address.longitude]):
        return Decimal('2000'), 0  # Default delivery fee if coordinates are missing

    # Calculate distance in **meters**, then convert to **kilometers**
    distance_km = calculate_distance(
        float(business.latitude),
        float(business.longitude),
        float(delivery_address.latitude),
        float(delivery_address.longitude)
    ) / 1000  # Convert meters to kilometers

    # If transport mode is provided, use its pricing
    if transport_mode:
        fee = transport_mode.base_price + (transport_mode.price_per_km * distance_km)
        fee = max(round(fee), float(transport_mode.base_price))
    else:
        # Default calculation (1200 TZS per km, minimum 1200 TZS)
        fee = max(round(distance_km * 1200), 1200)

    return Decimal(fee), distance_km  # Return fee and distance


def get_delivery_fee_for_customer(customer, cart, default_fee=Decimal('2000')):
    """
    Get appropriate delivery fee for a customer based on their addresses and cart.
    Returns the calculated delivery fee.
    """
    # Initialize with default value
    delivery_fee = default_fee
    
    # If user has a default address and cart has a business, calculate dynamic delivery fee
    if hasattr(customer, 'default_address') and customer.default_address and cart.business:
        delivery_fee, _ = calculate_delivery_fee(cart.business, customer.default_address)
    # If no default address but user has addresses, use the first one
    elif DeliveryAddress.objects.filter(customer=customer).exists() and cart.business:
        default_address = DeliveryAddress.objects.filter(customer=customer).first()
        delivery_fee, _ = calculate_delivery_fee(cart.business, default_address)
    
    return delivery_fee


# View functions

@login_required
def select_transport_mode(request):
    """View to select a transport mode for delivery"""
    try:
        # Get customer profile
        if not hasattr(request.user, 'customer_profile'):
            messages.error(request, 'Customer profile not found.')
            return redirect('customers:home')
        
        customer = request.user.customer_profile
        
        # Get customer's cart
        try:
            cart = Cart.objects.get(customer=customer)
            cart_items = cart.items.all()
            
            if not cart_items.exists():
                messages.info(request, 'Your cart is empty.')
                return redirect('customers:cart')
                
            # Calculate cart subtotal
            subtotal = sum(item.product.price * item.quantity for item in cart_items)
            cart.subtotal = subtotal
            
        except Cart.DoesNotExist:
            messages.error(request, 'No active cart found.')
            return redirect('customers:home')
        
        # Get available transport modes
        transport_modes = TransportMode.objects.filter(is_active=True)
        
        # Calculate initial delivery fee with the first transport mode
        initial_delivery_fee = 0
        if transport_modes.exists() and hasattr(customer, 'default_address') and customer.default_address:
            first_transport = transport_modes.first()
            initial_fee, _ = calculate_delivery_fee(cart.business, customer.default_address, first_transport)
            initial_delivery_fee = initial_fee
        
        context = {
            'transport_modes': transport_modes,
            'cart': cart,
            'initial_delivery_fee': initial_delivery_fee
        }
        
        return render(request, 'customers/transport_selection.html', context)
        
    except Exception as e:
        messages.error(request, f'Error selecting transport mode: {str(e)}')
        return redirect('customers:cart')


@login_required
def save_transport_mode(request):
    """Save the selected transport mode and redirect to checkout"""
    if request.method != 'POST':
        return redirect('customers:select_transport_mode')
    
    try:
        transport_mode_id = request.POST.get('transport_mode')
        
        if not transport_mode_id:
            messages.error(request, 'Please select a transport mode.')
            return redirect('customers:select_transport_mode')
        
        # Get transport mode
        transport_mode = get_object_or_404(TransportMode, id=transport_mode_id)
        
        # Store in session for checkout process
        request.session['selected_transport_mode_id'] = transport_mode.id
        
        return redirect('customers:checkout')
        
    except Exception as e:
        messages.error(request, f'Error saving transport mode: {str(e)}')
        return redirect('customers:select_transport_mode')


def calculate_delivery_fee_view(request):
    try:
        # Get address ID from request
        address_id = request.GET.get('address_id')

        if not address_id:
            return JsonResponse({'success': False, 'error': 'Missing address_id'}, status=400)

        # Fetch the delivery address object
        delivery_address = get_object_or_404(DeliveryAddress, id=address_id)
        
        # Get the user's cart and the associated business
        if not hasattr(request.user, 'customer_profile'):
            return JsonResponse({'success': False, 'error': 'User profile not found'}, status=400)
            
        try:
            cart = Cart.objects.get(customer=request.user.customer_profile)
            business = cart.business
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No active cart found'}, status=400)

        if not business:
            return JsonResponse({'success': False, 'error': 'Business information not found'}, status=400)

        # Now call your existing calculate_delivery_fee function
        delivery_fee, distance_km = calculate_delivery_fee(business, delivery_address)
        
        logger.info(f"Calculated delivery fee: {delivery_fee} TZS for distance between business ({business.latitude}, {business.longitude}) and address ({delivery_address.latitude}, {delivery_address.longitude})")

        return JsonResponse({'success': True, 'delivery_fee': float(delivery_fee), 'distance_km': float(distance_km)})

    except Exception as e:
        logger.error(f"Error calculating delivery fee: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def home(request):
    # Get businesses, excluding those from the user's region if the user has location data
    businesses_query = Business.objects.filter(is_active=True)
    
    # Get featured businesses
    featured_businesses = Business.objects.filter(is_featured=True, is_active=True)
    categories = Category.objects.all()
    
    # Check if user has location data
    user_region = None
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        if hasattr(customer, 'region') and customer.region:
            user_region = customer.region
        elif customer.latitude and customer.longitude:
            # Define regions with their approximate center coordinates
            regions = {
                'dar_es_salaam': {'lat': -6.7924, 'lng': 39.2083},
                'arusha': {'lat': -3.3869, 'lng': 36.6830},
                'mwanza': {'lat': -2.5164, 'lng': 32.9175},
                'dodoma': {'lat': -6.1630, 'lng': 35.7516},
                'tanga': {'lat': -5.0705, 'lng': 39.1089},
                'mbeya': {'lat': -8.9000, 'lng': 33.4500},
                'morogoro': {'lat': -6.8222, 'lng': 37.6616},
                'zanzibar': {'lat': -6.1659, 'lng': 39.1988},
            }
            
            # Determine user's region based on proximity to region centers
            min_distance = float('inf')
            lat = float(customer.latitude)
            lng = float(customer.longitude)
            
            for region_code, coords in regions.items():
                # Calculate rough distance using Pythagorean distance for quick comparison
                dist = math.sqrt((lat - coords['lat'])**2 + (lng - coords['lng'])**2)
                
                if dist < min_distance:
                    min_distance = dist
                    user_region = region_code
    
    # Filter businesses for "In Other Regions" section
    if user_region:
        # Get businesses from user's region for the "Popular in your region" section
        businesses_in_region = businesses_query.filter(region=user_region)
        
        # Get businesses from other regions for the "In Other Regions" section
        businesses_other_regions = businesses_query.exclude(region=user_region)
        
        # Use businesses from other regions for the "In Other Regions" section
        businesses = businesses_other_regions
    else:
        # No user region detected, show all businesses
        businesses = businesses_query
        businesses_in_region = []
    
    # Get cart count if user is authenticated
    cart_count = 0
    if request.user.is_authenticated:
        try:
            # Check if user has a customer profile
            if hasattr(request.user, 'customer_profile'):
                customer = request.user.customer_profile
                try:
                    cart = Cart.objects.get(customer=customer)
                    cart_count = sum(item.quantity for item in cart.items.all())
                except Cart.DoesNotExist:
                    pass
        except Exception as e:
            # Log the error but continue
            logger.error(f"Error getting customer profile: {str(e)}")
    
    context = {
        'businesses': businesses,
        'businesses_in_region': businesses_in_region,
        'featured_businesses': featured_businesses,
        'categories': categories,
        'cart_count': cart_count,
        'user_region': user_region,
        'user_region_display': dict(REGION_CHOICES).get(user_region, user_region.title() if user_region else None)
    }
    return render(request, 'customers/home.html', context)


def business_list(request):
    businesses = Business.objects.all()
    return render(request, 'customers/business_list.html', {'businesses': businesses})


def business_detail(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    products = Product.objects.filter(business=business)
    
    # Organize products by category
    products_with_category = products.select_related('category').order_by('category__id')
    
    # Group products by category
    products_by_category = {}
    for product in products_with_category:
        if product.category:
            if product.category not in products_by_category:
                products_by_category[product.category] = []
            products_by_category[product.category].append(product)
    
    # Check if user is logged in and has favorited this business
    is_favorite = False
    cart_count = 0
    
    if request.user.is_authenticated:
        try:
            # Check if user has a customer profile
            if hasattr(request.user, 'customer_profile'):
                customer = request.user.customer_profile
                is_favorite = False  # FavoriteBusiness.objects.filter(customer=customer, business=business).exists()
                
                # Get cart count
                try:
                    cart = Cart.objects.get(customer=customer)
                    cart_count = sum(item.quantity for item in cart.items.all())
                except Cart.DoesNotExist:
                    cart_count = 0
        except Exception as e:
            # Log the error but continue
            logger.error(f"Error getting customer profile: {str(e)}")
    
    # Check if business has cover_image and banner
    has_cover_image = business.cover_image is not None
    has_banner = hasattr(business, 'banner') and business.banner is not None
    
    context = {
        'business': business,
        'products': products,
        'products_by_category': products_by_category,
        'is_favorite': is_favorite,
        'has_cover_image': has_cover_image,
        'has_banner': has_banner,
        'cart_count': cart_count
    }
    
    return render(request, 'customers/business_detail.html', context)


def search(request):
    """Enhanced search for businesses and products"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    sort = request.GET.get('sort', 'relevance')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    # Start with all active businesses and products
    businesses = Business.objects.filter(is_active=True)
    products = Product.objects.all()
    
    # Apply search query if provided
    if query:
        businesses = businesses.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(address__icontains=query)
        )
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(business__name__icontains=query)
        )
    
    # Apply category filter
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            # Filter products by category
            products = products.filter(category=category)
            
            # Filter businesses to only show those with products in this category
            business_ids = products.values_list('business_id', flat=True).distinct()
            businesses = businesses.filter(id__in=business_ids)
        except Category.DoesNotExist:
            pass
    
    # Apply price range filters (for products only)
    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except (ValueError, TypeError):
            pass
            
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except (ValueError, TypeError):
            pass
    
    # Apply sorting
    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    elif sort == 'name_asc':
        products = products.order_by('name')
        businesses = businesses.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
        businesses = businesses.order_by('-name')
    
    # Get cart count for UI if user is authenticated
    cart_count = 0
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        try:
            cart = Cart.objects.get(customer=request.user.customer_profile)
            cart_count = sum(item.quantity for item in cart.items.all())
        except Cart.DoesNotExist:
            pass
    
    context = {
        'query': query,
        'businesses': businesses[:24],  # Limit results
        'products': products[:24],
        'categories': Category.objects.all(),
        'cart_count': cart_count
    }
    return render(request, 'customers/search.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Get related products from the same business and category
    related_products = Product.objects.filter(
        business=product.business, 
        category=product.category
    ).exclude(id=product.id)[:4]
    
    # If we don't have 4 related products in the same category, get more from the same business
    if related_products.count() < 4:
        additional_products = Product.objects.filter(
            business=product.business
        ).exclude(id=product.id).exclude(id__in=related_products.values_list('id', flat=True))[:4-related_products.count()]
        
        related_products = list(related_products) + list(additional_products)
    
    # Check if user has a cart and if this product is in it
    in_cart = False
    cart_count = 0
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        try:
            cart = Cart.objects.get(customer=customer)
            cart_count = sum(item.quantity for item in cart.items.all())
            in_cart = cart.items.filter(product=product).exists()
        except Cart.DoesNotExist:
            pass
    
    # Product type context
    is_gas_product = product.category and product.category.name.lower() == 'gas'
    is_food_product = product.category and product.category.name.lower() == 'food'
    
    context = {
        'product': product,
        'related_products': related_products,
        'in_cart': in_cart,
        'cart_count': cart_count,
        'is_gas_product': is_gas_product,
        'is_food_product': is_food_product,
        'business': product.business,  # Add business for consistent navigation
    }
    
    return render(request, 'customers/product_detail.html', context)


@login_required
def add_to_cart(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Get customer profile
        customer = get_or_create_customer_profile(request)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(customer=customer)
        
        # If cart is new or has a different business, clear existing items and set business
        if created or (cart.business and cart.business != product.business):
            cart.items.all().delete()
            cart.business = product.business
            cart.save()
        elif not cart.business:
            # If cart exists but has no business set, set it now
            cart.business = product.business
            cart.save()
        
        # Check if product already in cart
        try:
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 1}
            )
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                messages.error(request, "Product is already in cart.")
                return redirect('customers:cart')
            else:
                raise
        
        # If product already exists, increment quantity
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
        
        # If it's an AJAX request, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            cart_total = sum(item.quantity for item in cart.items.all())
            return JsonResponse({
                'success': True,
                'message': f"{product.name} added to your cart.",
                'cart_total': cart_total,
                'redirect_url': reverse('customers:cart')
            })
        
        # For regular requests, add a message and redirect
        messages.success(request, f"{product.name} added to your cart.")
        return redirect('customers:cart')
    except Exception as e:
        # Log the error
        logger.error(f"Error adding to cart: {str(e)}")
        
        # Return error response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': False,
                'error': f"Error adding to cart: {str(e)}"
            })
        
        # For regular requests, add error message and redirect
        messages.error(request, f"Error adding to cart: {str(e)}")
        return redirect('customers:business_detail', business_id=product.business.id)


@login_required
def update_cart_item_ajax(request, item_id):
    """Handle AJAX requests to update cart item quantity"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Get the data from the request
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        # Ensure customer profile exists
        customer = get_or_create_customer_profile(request)
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        # Check if item belongs to user's cart
        if cart_item.cart.customer != customer:
            return JsonResponse({
                'success': False,
                'error': "You don't have permission to update this item."
            })
        
        # Update quantity or remove if quantity is 0
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
        
        # Calculate new cart totals
        cart = cart_item.cart
        subtotal, cart_count = calculate_cart_totals(cart)
        
        # Calculate delivery fee
        delivery_fee = get_delivery_fee_for_customer(customer, cart)
        
        total = subtotal + delivery_fee
        
        # Return success response with updated data
        return JsonResponse({
            'success': True,
            'message': 'Cart updated successfully',
            'item_subtotal': float(cart_item.product.price * cart_item.quantity) if quantity > 0 else 0,
            'subtotal': float(subtotal),
            'delivery_fee': float(delivery_fee),
            'total': float(total),
            'cart_count': cart_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Error updating cart: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Error updating cart: {str(e)}'})


@login_required
def remove_from_cart(request, item_id):
    try:
        # Get customer profile
        customer = get_or_create_customer_profile(request)
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        # Check if item belongs to user's cart
        if cart_item.cart.customer != customer:
            messages.error(request, "You don't have permission to update this item.")
            return redirect('customers:cart')
        
        # Remove the item
        cart_item.delete()
        
        # Calculate new cart totals
        cart = cart_item.cart
        subtotal, cart_count = calculate_cart_totals(cart)
        
        # Calculate delivery fee
        delivery_fee = get_delivery_fee_for_customer(customer, cart)
        
        # Calculate total
        total = subtotal + delivery_fee
        
        # If it's an AJAX request, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'subtotal': float(subtotal),
                'delivery_fee': float(delivery_fee),
                'total': float(total),
                'cart_count': cart_count
            })
        
        # For regular requests, add a message and redirect
        messages.success(request, "Item removed from cart.")
        return redirect('customers:cart')
        
    except Exception as e:
        logger.error(f"Error removing item from cart: {str(e)}")
        
        # For AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        
        # For regular requests
        messages.error(request, f"Error removing item from cart: {str(e)}")
        return redirect('customers:cart')


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('customers:home')
        
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        # Add detailed logging of phone number format
        logger.info(f"Login attempt - Raw phone number: {phone}")
        
        # Check phone number format
        if phone and not phone.startswith('255'):
            logger.info(f"Adding 255 prefix to phone number: {phone}")
            # Try to format phone properly
            if phone.startswith('0'):
                phone = '255' + phone[1:]
                logger.info(f"Converted 0xxx format to: {phone}")
            elif phone.startswith('+255'):
                phone = phone[1:]  # Remove the + sign
                logger.info(f"Removed + sign from +255 format: {phone}")
            else:
                phone = '255' + phone
                logger.info(f"Added 255 prefix: {phone}")
        
        logger.info(f"Attempting authentication with phone: {phone}")
        user = authenticate(request, username=phone, password=password)
        
        if user is not None:
            logger.info(f"User authenticated successfully: {user.id}")
            login(request, user)
            next_url = request.GET.get('next', 'customers:home')
            return redirect(next_url)
        else:
            logger.error(f"Authentication failed for phone: {phone}")
            # Try alternate formats as fallback
            alternate_formats = []
            if phone.startswith('255'):
                alternate_formats.append('0' + phone[3:])  # Try with 0 prefix
                alternate_formats.append('+' + phone)  # Try with + prefix
            
            success = False
            for alt_phone in alternate_formats:
                logger.info(f"Trying alternate format: {alt_phone}")
                alt_user = authenticate(request, username=alt_phone, password=password)
                if alt_user is not None:
                    logger.info(f"Alternate format authentication successful: {alt_phone}")
                    login(request, alt_user)
                    next_url = request.GET.get('next', 'customers:home')
                    success = True
                    return redirect(next_url)
            
            if not success:
                logger.error("All authentication attempts failed")
                messages.error(request, 'Invalid phone number or password')
    
    return render(request, 'customers/login.html')


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('customers:home')
        
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            # Check if a user with this email already exists
            email = form.cleaned_data.get('email')
            phone = form.cleaned_data.get('phone')
            
            if CustomUser.objects.filter(email=email).exists() and email:
                # User is already registered with this email
                messages.info(request, 'An account with this email already exists. Please log in.')
                return render(request, 'customers/already_registered.html', {
                    'email': email,
                    'login_url': reverse('customers:login')
                })
            
            # Check if a user with this phone number already exists
            if CustomUser.objects.filter(phone=phone).exists():
                # Phone number is already registered
                messages.error(request, 'This phone number is already registered. Please use a different number or log in.')
                return render(request, 'customers/register.html', {'form': form})
                
            # If no existing user, create new account
            try:
                user = form.save()
                # Create customer profile
                CustomerProfile.objects.create(user=user, phone_number=phone)
                # Log the user in
                login(request, user)
                return redirect('customers:home')
            except Exception as e:
                # Handle any database integrity errors (like duplicate phone number in profile)
                logger.error(f"Error creating user account: {str(e)}")
                messages.error(request, 'This phone number is already registered. Please use a different number or log in.')
                return render(request, 'customers/register.html', {'form': form})
    else:
        form = CustomerSignUpForm()
    
    return render(request, 'customers/register.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('customers:home')


def select_transport_mode(request):
    """View to select transportation mode before final checkout"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'Please complete your profile before checkout.')
        return redirect('customers:edit_profile')

    customer = request.user.customer_profile
    try:
        cart = Cart.objects.get(customer=customer)
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('customers:home')
    
    if cart.items.count() == 0:
        messages.error(request, 'Your cart is empty.')
        return redirect('customers:home')
    
    # Get customer's default address or first address
    delivery_address = None
    if customer.default_address:
        delivery_address = customer.default_address
    elif customer.addresses.exists():
        delivery_address = customer.addresses.first()
    
    # Calculate distance if we have both business and delivery address
    distance_km = 0
    initial_delivery_fee = Decimal('2000')  # Default fee
    
    if cart.business and delivery_address and all([cart.business.latitude, cart.business.longitude, 
                                                  delivery_address.latitude, delivery_address.longitude]):
        initial_delivery_fee, distance_km = calculate_delivery_fee(cart.business, delivery_address)
    
    # Get active transport modes
    transport_modes = TransportMode.objects.filter(is_active=True).order_by('base_price')
    
    # Calculate total with default delivery fee
    total = cart.subtotal + initial_delivery_fee
    
    return render(request, 'customers/transport_selection.html', {
        'cart': cart,
        'transport_modes': transport_modes,
        'distance_km': distance_km,
        'initial_delivery_fee': initial_delivery_fee,
        'total': total
    })


@login_required
def save_transport_mode(request):
    """Save selected transport mode and redirect to checkout"""
    if request.method != 'POST':
        return redirect('customers:select_transport_mode')
    
    transport_mode_id = request.POST.get('transport_mode')
    distance_km = request.POST.get('distance_km', 0)
    delivery_fee = request.POST.get('delivery_fee', 2000)
    
    # Store in session
    request.session['selected_transport_mode_id'] = transport_mode_id
    request.session['calculated_distance_km'] = float(distance_km)
    request.session['calculated_delivery_fee'] = float(delivery_fee)
    
    return redirect('customers:checkout')


@login_required
def checkout(request, business_id=None):
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'Please complete your profile before checkout.')
        return redirect('customers:edit_profile')

    customer = request.user.customer_profile
    try:
        cart = Cart.objects.get(customer=customer)
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('customers:home')
    
    if cart.items.count() == 0:
        messages.error(request, 'Your cart is empty.')
        return redirect('customers:home')
        
    # Check if transport mode has been selected
    if 'selected_transport_mode_id' not in request.session:
        return redirect('customers:select_transport_mode')
    
    # Get delivery fee from session (calculated during transport selection)
    delivery_fee = Decimal(str(request.session.get('calculated_delivery_fee', 2000)))
    
    # Get delivery addresses
    delivery_addresses = customer.addresses.all()
    
    # Get selected transport mode
    transport_mode = None
    transport_mode_id = request.session.get('selected_transport_mode_id')
    if transport_mode_id:
        try:
            transport_mode = TransportMode.objects.get(id=transport_mode_id)
        except TransportMode.DoesNotExist:
            pass

    total = cart.subtotal + delivery_fee
    
    return render(request, 'customers/checkout.html', {
        'cart': cart,
        'delivery_addresses': delivery_addresses,
        'delivery_fee': delivery_fee,
        'total': total,
        'transport_mode': transport_mode
    })


@login_required
def place_order(request):
    if request.method != 'POST':
        return redirect('customers:checkout')

    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'Please complete your profile before placing an order.')
        return redirect('customers:edit_profile')

    customer = request.user.customer_profile

    # Get cart
    try:
        cart = Cart.objects.get(customer=customer)
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('customers:home')
    
    # Get selected transport mode
    transport_mode = None
    transport_mode_id = request.session.get('selected_transport_mode_id')
    if transport_mode_id:
        try:
            transport_mode = TransportMode.objects.get(id=transport_mode_id)
        except TransportMode.DoesNotExist:
            pass
    
    # Get delivery address
    address_id = request.POST.get('delivery_address')
    if not address_id:
        messages.error(request, 'Please select a delivery address.')
        return redirect('customers:checkout')
    
    delivery_address = get_object_or_404(DeliveryAddress, id=address_id, customer=customer)
    
    # Get payment method
    payment_method = request.POST.get('payment_method', 'cash')
    
    # Calculate delivery fee
    delivery_fee = Decimal(str(request.session.get('calculated_delivery_fee', 2000)))
    
    # Additional fees
    surge_fee = Decimal('0')
    bulk_discount = Decimal('0')
    
    # Notes
    notes = request.POST.get('notes', '')
    
    # Create order
    order = Order.objects.create(
        customer=customer,
        business=cart.business,
        delivery_address=delivery_address,
        payment_method=payment_method,
        subtotal=cart.subtotal,
        delivery_fee=delivery_fee,
        transport_mode=transport_mode,  # Add the selected transport mode
        total=cart.subtotal + delivery_fee + surge_fee - bulk_discount,
        notes=notes,
        status='pending'
    )
    
    # Create order items
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            notes=item.notes if hasattr(item, 'notes') else ''
        )
    
    # Clear cart
    cart.items.all().delete()
    
    # Clear session data
    if 'selected_transport_mode_id' in request.session:
        del request.session['selected_transport_mode_id']
    if 'calculated_delivery_fee' in request.session:
        del request.session['calculated_delivery_fee']
    if 'calculated_distance_km' in request.session:
        del request.session['calculated_distance_km']
    
    return redirect('customers:order_confirmation', order_id=order.id)


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user.customer_profile)
    return render(request, 'customers/order_confirmation.html', {'order': order})


@login_required
def order_history(request):
    customer = request.user.customer_profile
    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    
    context = {
        'orders': orders
    }
    return render(request, 'customers/order_history.html', context)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Ensure user owns this order
    if order.customer.user != request.user:
        messages.error(request, "You don't have permission to view this order.")
        return redirect('order_history')
    
    context = {
        'order': order,
        'items': order.items.all()
    }
    return render(request, 'customers/order_detail.html', context)


@login_required
def set_default_address(request):
    """Set an address as the default for a customer"""
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        if address_id:
            address = get_object_or_404(DeliveryAddress, id=address_id, customer=request.user.customer_profile)
            address.is_default = True
            address.save()
            messages.success(request, "Default address updated successfully.")
        else:
            messages.error(request, "No address selected.")
    
    return redirect('customers:manage_addresses')


@login_required
def toggle_favorite_business(request):
    """Toggle a business as favorite for the customer"""
    if request.method == 'POST':
        business_id = request.POST.get('business_id')
        if business_id:
            business = get_object_or_404(Business, id=business_id)
            customer = request.user.customer_profile
            
            if business in customer.favorite_businesses.all():
                customer.favorite_businesses.remove(business)
                is_favorite = False
                message = f"Removed {business.name} from favorites."
            else:
                customer.favorite_businesses.add(business)
                is_favorite = True
                message = f"Added {business.name} to favorites."
                
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'is_favorite': is_favorite,
                    'message': message
                })
            else:
                messages.success(request, message)
                return redirect('customers:business_detail', business_id=business.id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    return redirect('customers:home')


@login_required
def manage_addresses(request):
    """View to manage all delivery addresses for a customer"""
    customer = request.user.customer_profile
    addresses = DeliveryAddress.objects.filter(customer=customer)
    
    context = {
        'addresses': addresses
    }
    return render(request, 'customers/manage_addresses.html', context)


@login_required
def featured_business_checkout(request, business_id):
    # Get the business
    business = get_object_or_404(Business, id=business_id)
    
    # Get the customer profile
    customer = request.user.customer_profile
    
    # Get the cart for this business
    try:
        cart = Cart.objects.get(customer=customer, business=business)
    except Cart.DoesNotExist:
        messages.error(request, "Cart is empty. Please add products before checkout.")
        return redirect('customers:business_detail', business_id=business_id)
    
    # Calculate special delivery fee (flat fee for now - could be dynamic in future)
    special_delivery_fee = 5000  # Example: 5000 TZS
    
    # Calculate total
    total_amount = cart.subtotal + special_delivery_fee
    
    context = {
        'business': business,
        'customer': customer,
        'cart': cart,
        'special_delivery_fee': special_delivery_fee,
        'total_amount': total_amount
    }
    
    return render(request, 'customers/featured_checkout.html', context)


@login_required
def place_featured_order(request):
    if request.method == 'POST':
        business_id = request.POST.get('business_id')
        
        # Get the business
        business = get_object_or_404(Business, id=business_id)
        customer = request.user.customer_profile
        
        try:
            cart = Cart.objects.get(customer=customer, business=business)
        except Cart.DoesNotExist:
            messages.error(request, "Cart is empty. Please add products before checkout.")
            return redirect('customers:business_detail', business_id=business_id)
        
        # Special delivery fee
        special_delivery_fee = 5000  # Same as in featured_business_checkout
        
        # Create a new order
        order = Order.objects.create(
            customer=customer,
            business=business,
            status='pending',
            delivery_fee=special_delivery_fee,
            subtotal=cart.subtotal,
            total=cart.subtotal + special_delivery_fee,
            special_delivery=True,  # Flag to indicate this is a special delivery order
            order_type='pickup'  # Set to pickup since customer will pick up from the local office
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.total_price
            )
        
        # Clear the cart
        cart.items.all().delete()
        
        messages.success(request, "Your order has been placed successfully! We will notify you when it arrives at our office.")
        return redirect('customers:order_detail', order_id=order.id)
    
    # If not POST, redirect to home
    return redirect('customers:home')


@login_required
def add_address(request):
    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = request.user.customer_profile
            address.save()
            messages.success(request, "Address added successfully!")
            
            # If next parameter is provided, redirect to that URL
            next_url = request.GET.get('next')
            if next_url == 'checkout':
                return redirect('customers:checkout')
            
            return redirect('customers:manage_addresses')
    else:
        form = DeliveryAddressForm()
    
    return render(request, 'customers/add_address.html', {'form': form})


@login_required
def edit_address(request, address_id):
    """View to edit a customer address"""
    address = get_object_or_404(DeliveryAddress, id=address_id, customer=request.user.customer_profile)
    
    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully.")
            return redirect('customers:manage_addresses')
    else:
        form = DeliveryAddressForm(instance=address)
    
    return render(request, 'customers/edit_address.html', {'form': form, 'address': address})


@login_required
def delete_address(request, address_id):
    """View to delete a customer address"""
    address = get_object_or_404(DeliveryAddress, id=address_id, customer=request.user.customer_profile)
    
    was_default = address.is_default
    address.delete()
    
    # If we deleted the default address, set another one as default
    if was_default:
        other_address = DeliveryAddress.objects.filter(customer=request.user.customer_profile).first()
        if other_address:
            other_address.is_default = True
            other_address.save()
    
    messages.success(request, "Address deleted successfully.")
    return redirect('customers:manage_addresses')


@login_required
def add_address_from_coordinates(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Parse JSON data
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return JsonResponse({'success': False, 'error': 'Latitude and longitude are required'})
        
        # Create a basic address with the coordinates
        customer = request.user.customer_profile
        new_address = DeliveryAddress.objects.create(
            customer=customer,
            name="Current Location",
            street="Auto-detected location",
            area="Unknown",
            city="Unknown",
            latitude=latitude,
            longitude=longitude,
            is_default=not DeliveryAddress.objects.filter(customer=customer).exists()  # Make default if first address
        )
        
        return JsonResponse({
            'success': True, 
            'address_id': new_address.id,
            'message': 'Address created successfully'
        })
    
    except Exception as e:
        logger.error(f"Error creating address from coordinates: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


def nearby_businesses_api(request):
    """API endpoint for nearby businesses based on geolocation"""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    
    if not lat or not lng:
        return JsonResponse({'error': 'Latitude and longitude are required'}, status=400)
    
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return JsonResponse({'error': 'Invalid latitude or longitude'}, status=400)
    
    # Define regions with their approximate center coordinates
    regions = {
        'dar_es_salaam': {'lat': -6.7924, 'lng': 39.2083},
        'arusha': {'lat': -3.3869, 'lng': 36.6830},
        'mwanza': {'lat': -2.5164, 'lng': 32.9175},
        'dodoma': {'lat': -6.1630, 'lng': 35.7516},
        'tanga': {'lat': -5.0705, 'lng': 39.1089},
        'mbeya': {'lat': -8.9000, 'lng': 33.4500},
        'morogoro': {'lat': -6.8222, 'lng': 37.6616},
        'zanzibar': {'lat': -6.1659, 'lng': 39.1988},
    }
    
    # Determine user's region based on proximity to region centers
    user_region = None
    min_distance = float('inf')
    
    for region_code, coords in regions.items():
        # Calculate rough distance using Pythagorean distance for quick comparison
        dist = math.sqrt((lat - coords['lat'])**2 + (lng - coords['lng'])**2)
        
        if dist < min_distance:
            min_distance = dist
            user_region = region_code
    
    # Get active businesses
    businesses_data = []
    featured_businesses = []
    regional_businesses = []
    
    # Get all active businesses
    all_businesses = Business.objects.filter(is_active=True)
    
    # Process businesses
    for business in all_businesses:
        try:
            # Calculate distance if business has coordinates
            distance = None
            if business.latitude and business.longitude:
                distance = calculate_distance(
                    lat, 
                    lng, 
                    float(business.latitude), 
                    float(business.longitude)
                ) / 1000  # Convert meters to kilometers
            
            business_data = {
                'id': business.id,
                'name': business.name,
                'description': business.address,
                'region': business.get_region_display() if hasattr(business, 'get_region_display') else None,
                'distance': round(distance, 1) if distance else None,
                'image': business.cover_image.url if hasattr(business, 'cover_image') and business.cover_image else None,
                'rating': business.rating if hasattr(business, 'rating') else 0,
                'is_featured': business.is_featured if hasattr(business, 'is_featured') else False,
                'same_region': business.region == user_region if hasattr(business, 'region') else False,
            }
            
            # Categorize businesses
            if hasattr(business, 'is_featured') and business.is_featured:
                featured_businesses.append(business_data)
                
            if hasattr(business, 'region') and business.region == user_region:
                regional_businesses.append(business_data)
            
            businesses_data.append(business_data)
            
        except Exception as e:
            # Skip businesses that cause errors
            logger.error(f"Error processing business {business.id}: {str(e)}")
            continue
    
    # Sort all businesses by distance
    businesses_data = sorted(businesses_data, key=lambda x: x['distance'] if x['distance'] else float('inf'))
    
    # Sort regional businesses by distance
    regional_businesses = sorted(regional_businesses, key=lambda x: x['distance'] if x['distance'] else float('inf'))

    # Sort featured businesses by distance
    featured_businesses = sorted(featured_businesses, key=lambda x: x['distance'] if x['distance'] else float('inf'))

    # Limit to nearest 20 businesses and 10 featured businesses
    businesses_data = businesses_data[:20]
    featured_businesses = featured_businesses[:10]

    # Get the region display name
    region_display_name = dict(REGION_CHOICES).get(user_region, user_region.title() if user_region else None)

    return JsonResponse({
        'all_businesses': businesses_data,
        'regional_businesses': regional_businesses,
        'featured_businesses': featured_businesses,
        'user_region': user_region,
        'region_name': region_display_name
    })


@login_required
def update_cart(request):
    """Update cart item quantity"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 0))
        
        if not item_id:
            messages.error(request, "No item specified.")
            return redirect('customers:cart')
        
        try:
            # Get customer profile
            customer = get_or_create_customer_profile(request)
            
            # Get cart item
            cart_item = get_object_or_404(CartItem, id=item_id)
            
            # Check if item belongs to user's cart
            if cart_item.cart.customer != customer:
                messages.error(request, "You don't have permission to update this item.")
                return redirect('customers:cart')
                
            # Update quantity
            if quantity < 1:
                quantity = 1
            
            cart_item.quantity = quantity
            cart_item.save()
            
            messages.success(request, "Cart updated.")
            return redirect('customers:cart')
            
        except Exception as e:
            logger.error(f"Error updating cart: {str(e)}")
            messages.error(request, f"Error updating cart: {str(e)}")
            return redirect('customers:cart')
    
    return redirect('customers:cart')


@login_required
def cart_view(request):
    try:
        # Get customer profile
        customer = get_or_create_customer_profile(request)
            
        cart = Cart.objects.get(customer=customer)
        cart_items = cart.items.all()
        
        # Calculate cart totals
        subtotal, cart_count = calculate_cart_totals(cart)
        
        # Get delivery fee
        delivery_fee = get_delivery_fee_for_customer(customer, cart)
        
        # Calculate total
        total = subtotal + delivery_fee
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'total': total,
            'cart_count': cart_count
        }
        
    except Cart.DoesNotExist:
        context = {
            'cart_items': [],
            'subtotal': 0,
            'delivery_fee': 0,
            'total': 0,
            'cart_count': 0
        }
    
    return render(request, 'customers/cart.html', context)


@login_required
def profile(request):
    """View to display and update user profile information"""
    if not hasattr(request.user, 'customer_profile'):
        from customers.models import CustomerProfile
        try:
            customer = CustomerProfile.objects.get(user=request.user)
        except CustomerProfile.DoesNotExist:
            customer = CustomerProfile.objects.create(
                user=request.user,
                phone_number=f"temp_{request.user.id}"
            )
    else:
        customer = request.user.customer_profile
    
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            profile = form.save(commit=False)
            
            # Explicitly handle the profile image if it's in the request
            if 'profile_image' in request.FILES:
                profile.profile_image = request.FILES['profile_image']

            profile.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('customers:profile')
        else:
            # Log form errors for debugging
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, f"Error updating profile: {form.errors}")
    else:
        form = CustomerProfileForm(instance=customer)

    # Get user orders for profile view
    orders = Order.objects.filter(customer=customer).order_by('-created_at')[:5]
    addresses = DeliveryAddress.objects.filter(customer=customer)
    favorite_businesses = Favorite.objects.filter(customer=customer).select_related('business')

    context = {
        'form': form,
        'customer': customer,
        'recent_orders': orders,
        'addresses': addresses,
        'favorite_businesses': favorite_businesses
    }
    return render(request, 'customers/profile.html', context)


@login_required
def save_user_location(request):
    """API endpoint to save user's location to their profile"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        # Parse JSON data
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return JsonResponse({'success': False, 'error': 'Latitude and longitude are required'})
        
        # Update user's profile with location
        customer = get_or_create_customer_profile(request)
        customer.last_known_latitude = latitude
        customer.last_known_longitude = longitude
        customer.location_updated_at = timezone.now()
        customer.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Location saved successfully'
        })
    
    except Exception as e:
        logger.error(f"Error saving user location: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})