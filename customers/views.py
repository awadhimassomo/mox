from django.db import connection
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required 
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Q, Count, Avg
from django.utils import timezone
import json
import uuid
import datetime
import math
import random
import requests

import string 
from decimal import Decimal
from itertools import groupby
from django.db.models.functions import Abs

from riders.models import Rider
from django.db.models import F, ExpressionWrapper, FloatField
from django.db.models.functions import Abs


from business.models import Business, Product, Category, REGION_CHOICES
from riders.utils import calculate_distance
from .models import CustomerProfile, DeliveryAddress, Cart, CartItem, Favorite
from orders.models import Order, OrderAssignmentGroup, OrderItem
from .forms import CustomerProfileForm, DeliveryAddressForm, CustomerSignUpForm
from operations.models import CustomUser as User
from riders.models import Rider as RiderProfile

import logging



def calculate_delivery_fee(business, delivery_address):
    """
    Calculate delivery fee based on distance between business and delivery address.
    Rate is 1200 TZS per kilometer, with a minimum fee of 1200 TZS.
    """
    # Ensure both business and delivery address have coordinates
    if not all([business.latitude, business.longitude, delivery_address.latitude, delivery_address.longitude]):
        return Decimal('2000')  # Default delivery fee if coordinates are missing

    # Calculate distance in **meters**, then convert to **kilometers**
    distance_km = calculate_distance(
        float(business.latitude),
        float(business.longitude),
        float(delivery_address.latitude),
        float(delivery_address.longitude)
    ) / 1000  # Convert meters to kilometers

    # Calculate the delivery fee (1200 TZS per km, minimum 1200 TZS)
    fee = max(round(distance_km * 1200), 1200)

    return Decimal(fee)  # Return as Decimal for consistency with Django models



logger = logging.getLogger(__name__)

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
        delivery_fee = calculate_delivery_fee(business, delivery_address)
        
        logger.info(f"Calculated delivery fee: {delivery_fee} TZS for distance between business ({business.latitude}, {business.longitude}) and address ({delivery_address.latitude}, {delivery_address.longitude})")

        return JsonResponse({'success': True, 'delivery_fee': float(delivery_fee)})

    except Exception as e:
        logger.error(f"Error calculating delivery fee: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def home(request):
    businesses = Business.objects.all()
    featured_businesses = Business.objects.filter(is_featured=True)
    categories = Category.objects.all()
    
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
            print(f"Error getting customer profile: {str(e)}")
    
    context = {
        'businesses': businesses,
        'featured_businesses': featured_businesses,
        'categories': categories,
        'cart_count': cart_count
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
            print(f"Error getting customer profile: {str(e)}")
    
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
    """Search businesses and products"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    
    businesses = Business.objects.all()
    products = Product.objects.all()
    
    if query:
        businesses = businesses.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category_id:
        category = get_object_or_404(Category, id=category_id)
        products = products.filter(category=category)
    
    context = {
        'query': query,
        'businesses': businesses[:20],  # Limit results
        'products': products[:20],
        'categories': Category.objects.all()
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
        
        # Check if user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            # Try to get an existing profile first
            from customers.models import CustomerProfile
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
        print(f"Error adding to cart: {str(e)}")
        
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
def cart_view(request):
    try:
        # Check if user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            # Try to get an existing profile first
            from customers.models import CustomerProfile
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
            
        cart = Cart.objects.get(customer=customer)
        cart_items = cart.items.all()
        
        # Calculate subtotal
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        
        # Initialize delivery fee with default value
        delivery_fee = Decimal('2000')  # Default fee
        
        # If user has a default address and cart has a business, calculate dynamic delivery fee
        if hasattr(customer, 'default_address') and customer.default_address and cart.business:
            delivery_fee = calculate_delivery_fee(cart.business, customer.default_address)
        # If no default address but user has addresses, use the first one
        elif DeliveryAddress.objects.filter(customer=customer).exists() and cart.business:
            default_address = DeliveryAddress.objects.filter(customer=customer).first()
            delivery_fee = calculate_delivery_fee(cart.business, default_address)
        
        # Calculate total
        total = subtotal + delivery_fee
        
        # Update cart count for the navbar
        cart_count = sum(item.quantity for item in cart_items)
        
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
def update_cart_item(request, item_id):
    if request.method != 'POST':
        return redirect('customers:cart')
    
    try:
        # Check if user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            # Try to get an existing profile first
            from customers.models import CustomerProfile
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
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        # Check if item belongs to user's cart
        if cart_item.cart.customer != customer:
            messages.error(request, "You don't have permission to update this item.")
            return redirect('customers:cart')
        
        # Update quantity
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            quantity = 1
        
        cart_item.quantity = quantity
        cart_item.save()
        
        messages.success(request, "Cart updated.")
        return redirect('customers:cart')
    
    except Exception as e:
        messages.error(request, f"Error updating cart: {str(e)}")
        return redirect('customers:cart')

@login_required
def remove_from_cart(request, item_id):
    try:
        # Check if user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            # Try to get an existing profile first
            from customers.models import CustomerProfile
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
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        # Check if item belongs to user's cart
        if cart_item.cart.customer != customer:
            messages.error(request, "You don't have permission to remove this item.")
            return redirect('customers:cart')
        
        # Remove item
        cart_item.delete()
        
        messages.success(request, "Item removed from cart.")
        return redirect('customers:cart')
    
    except Exception as e:
        messages.error(request, f"Error removing item: {str(e)}")
        return redirect('customers:cart')

@login_required
def checkout(request, business_id=None):
    try:
        # Check if user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            # Try to get an existing profile first
            from customers.models import CustomerProfile
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
        
        # Get cart and items
        cart = Cart.objects.get(customer=customer)
        
        # If business_id is provided, filter items to only show from that business
        if business_id:
            business = get_object_or_404(Business, id=business_id)
            cart_items = cart.items.filter(product__business=business)
            # Update the cart's business if it's from a specific business
            if not cart.business:
                cart.business = business
                cart.save()
        else:
            cart_items = cart.items.all()
        
        if not cart_items.exists():
            messages.warning(request, "Your cart is empty.")
            return redirect('customers:cart')
        
        # Get delivery addresses
        delivery_addresses = DeliveryAddress.objects.filter(customer=customer)
        
        # Initialize delivery fee and total
        delivery_fee = Decimal('2000')  # Default fee
        
        # If we have a default address and business has coordinates, calculate fee
        if delivery_addresses.filter(is_default=True).exists() and cart.business:
            default_address = delivery_addresses.get(is_default=True)
            delivery_fee = calculate_delivery_fee(cart.business, default_address)
        
        total = sum(item.product.price * item.quantity for item in cart_items) + delivery_fee
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'subtotal': sum(item.product.price * item.quantity for item in cart_items),
            'delivery_fee': delivery_fee,
            'total': total,
            'delivery_addresses': delivery_addresses,
            'cart_count': sum(item.quantity for item in cart_items)
        }
        
        return render(request, 'customers/checkout.html', context)
    
    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty.")
        return redirect('customers:cart')

@login_required
def place_order(request):
    if request.method != 'POST':
        return redirect('customers:checkout')

    try:
        logger.info("📌 Starting Order Placement")

        # Ensure user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            customer = CustomerProfile.objects.get_or_create(user=request.user)[0]
        else:
            customer = request.user.customer_profile

        logger.info(f"✅ Customer Profile Found: {customer}")

        # Get cart and items
        cart = Cart.objects.get(customer=customer)
        cart_items = cart.items.all()

        if not cart_items.exists():
            messages.warning(request, "Your cart is empty.")
            return redirect('customers:cart')

        logger.info(f"🛒 Cart Found: {cart_items.count()} items")

        # Get delivery address
        address_id = request.POST.get('delivery_address')
        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect('customers:checkout')

        delivery_address = get_object_or_404(DeliveryAddress, id=address_id, customer=customer)
        logger.info(f"📍 Delivery Address Selected: {delivery_address}")

        # Get payment method (default to cash)
        payment_method = request.POST.get('payment_method', 'cash')

        # Fetch the correct business instance
        business = get_object_or_404(Business, id=cart.business.id)
        logger.info(f"🏢 Business Found: {business.name}")

        # Generate a unique order number that starts with "MO-"
        timestamp = timezone.now().strftime('%y%m%d%H%M')
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order_number = f"MO-{timestamp}{random_chars}"
        logger.info(f"🔢 Generated Order Number: {order_number}")

        # Calculate subtotal first
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        
        # Calculate delivery fee based on the selected address
        delivery_fee = calculate_delivery_fee(business, delivery_address)
        logger.info(f"💰 Calculated Delivery Fee: {delivery_fee}")

        # Step 1: Create the Order with all required fields
        order = Order(
            order_number=order_number,
            customer=customer,  # Link to customer profile
            business=business,  # Link to business
            customer_name=f"{customer.user.first_name or 'Guest'} {customer.user.last_name or 'Customer'}",
            pickup_location=business,
            delivery_address=delivery_address,  # Link to delivery address object
            delivery_location=f"{delivery_address.street}, {delivery_address.area}, {delivery_address.city}",
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=subtotal + delivery_fee,
            payment_method=payment_method.upper(),
            payment_status='PENDING',
            status='PENDING'
        )
        
        # Set delivery coordinates
        if delivery_address.latitude and delivery_address.longitude:
            order.delivery_latitude = delivery_address.latitude
            order.delivery_longitude = delivery_address.longitude
            
        # Save the order to get a primary key
        order.save()
        logger.info(f"✅ Order Successfully Saved with ID: {order.id}")

        # Step 2: Add Order Items AFTER Order Has a Primary Key
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price,
                total_price=cart_item.product.price * cart_item.quantity,
                notes=cart_item.notes if hasattr(cart_item, 'notes') else ''
            )

        logger.info(f"📦 Order Items Added: {cart_items.count()} items")

        # Clear cart after order is placed
        cart_items.delete()
        logger.info("🛒 Cart Cleared After Order Placement")

        return redirect('customers:order_confirmation', order_id=order.id)

    except Exception as e:
        logger.error(f"⚠️ ERROR placing order: {str(e)}")
        messages.error(request, f"ERROR placing order: {str(e)}")
        return redirect('customers:checkout')


@login_required
def order_confirmation(request, order_id):
    try:
        # Check if user has a customer profile
        if not hasattr(request.user, 'customer_profile'):
            # Try to get an existing profile first
            from customers.models import CustomerProfile
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
        
        # Get order
        order = get_object_or_404(Order, id=order_id, customer=customer)
        order_items = order.items.all()
        
        # Check if there's an active rider assignment
        rider_assignment = None
        assigned_rider = None
        
        try:
            # Get the latest active assignment group
            from orders.models import OrderAssignmentGroup
            assignment_group = OrderAssignmentGroup.objects.filter(
                order=order,
                is_active=True
            ).latest('created_at')
            
            if assignment_group and not assignment_group.is_expired():
                rider_assignment = assignment_group
        except OrderAssignmentGroup.DoesNotExist:
            pass
        
        # Check if a rider has been assigned - safely check if rider attribute exists
        assigned_rider = None
        try:
            if hasattr(order, 'rider') and order.rider:
                assigned_rider = order.rider
        except Exception as e:
            print(f"Error checking rider: {str(e)}")
            # Continue execution even if rider check fails
        
        context = {
            'order': order,
            'order_items': order_items,
            'rider_assignment': rider_assignment,
            'assigned_rider': assigned_rider,
            'cart_count': 0  # Cart should be empty after order
        }
        
        return render(request, 'customers/order_confirmation.html', context)
    
    except Exception as e:
        messages.error(request, f"Error retrieving order: {str(e)}")
        return redirect('customers:order_history')

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

def customer_signup(request):
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create customer profile
            CustomerProfile.objects.create(
                user=user,
                phone=user.phone
            )
            
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('home')
    else:
        form = CustomerSignUpForm()
    
    return render(request, 'customers/signup.html', {'form': form})

@login_required
def profile(request):
    customer = request.user.customer_profile
    addresses = DeliveryAddress.objects.filter(customer=customer)
    
    context = {
        'customer': customer,
        'addresses': addresses
    }
    return render(request, 'customers/profile.html', context)

@login_required
def edit_profile(request):
    customer = request.user.customer_profile
    
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = CustomerProfileForm(instance=customer)
    
    return render(request, 'customers/edit_profile.html', {'form': form})

@login_required
def add_address(request):
    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = request.user.customer_profile
            address.save()
            messages.success(request, "Address added successfully!")
            return redirect('profile')
    else:
        form = DeliveryAddressForm()
    
    return render(request, 'customers/add_address.html', {'form': form})

@login_required
def edit_address(request, address_id):
    """View to edit a customer address"""
    try:
        # Get the address
        address = get_object_or_404(DeliveryAddress, id=address_id)
        
        # Verify ownership
        if address.customer.user != request.user:
            messages.error(request, "You don't have permission to edit this address.")
            return redirect('customers:manage_addresses')
        
        if request.method == 'POST':
            # Process form data
            street = request.POST.get('street')
            area = request.POST.get('area')
            city = request.POST.get('city')
            notes = request.POST.get('notes')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            
            # Update address
            address.street = street
            address.area = area
            address.city = city
            address.notes = notes
            
            # Update coordinates if provided
            if latitude and longitude:
                address.latitude = latitude
                address.longitude = longitude
                
            address.save()
            messages.success(request, "Address updated successfully.")
            return redirect('customers:manage_addresses')
        
        # Render form with current data
        return render(request, 'customers/edit_address.html', {'address': address})
    
    except Exception as e:
        messages.error(request, f"Error editing address: {str(e)}")
        return redirect('customers:manage_addresses')

@login_required
def delete_address(request, address_id):
    """View to delete a customer address"""
    try:
        # Get the address
        address = get_object_or_404(DeliveryAddress, id=address_id)
        
        # Verify ownership
        if address.customer.user != request.user:
            messages.error(request, "You don't have permission to delete this address.")
            return redirect('customers:manage_addresses')
        
        # Check if this is the default address
        is_default = address.is_default
        
        # Delete the address
        address.delete()
        
        # If we deleted the default address, set another one as default if available
        if is_default:
            other_address = DeliveryAddress.objects.filter(customer=address.customer).first()
            if other_address:
                other_address.is_default = True
                other_address.save()
        
        messages.success(request, "Address deleted successfully.")
        
    except Exception as e:
        messages.error(request, f"Error deleting address: {str(e)}")
    
    return redirect('customers:manage_addresses')

@login_required
def update_cart(request):
    """Update cart item quantity"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 0))
        
        cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user.customer_profile)
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
        
        messages.success(request, "Cart updated successfully.")
    
    return redirect('cart_view')

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
                
            if request.is_ajax():
                return JsonResponse({
                    'success': True,
                    'is_favorite': is_favorite,
                    'message': message
                })
            else:
                messages.success(request, message)
                return redirect('customers:business_detail', business_id=business.id)
    
    if request.is_ajax():
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    return redirect('customers:home')

def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('customers:home')
        
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        user = authenticate(request, username=phone, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'customers:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid phone number or password')
    
    return render(request, 'customers/login.html')

def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('customers:home')
        
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create customer profile
            CustomerProfile.objects.create(user=user)
            # Log the user in
            login(request, user)
            return redirect('customers:home')
    else:
        form = CustomerSignUpForm()
    
    return render(request, 'customers/register.html', {'form': form})

def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('customers:home')

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
    
    # More accurate distance calculation using Haversine formula
    def calculate_distance(lat1, lng1, lat2, lng2):
        # Haversine formula for more accurate distance calculation
        R = 6371  # Earth radius in kilometers
        
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(float(lat1))
        lng1_rad = math.radians(float(lng1))
        lat2_rad = math.radians(float(lat2))
        lng2_rad = math.radians(float(lng2))
        
        # Differences in coordinates
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    # Determine user's region based on proximity to region centers
    user_region = None
    min_distance = float('inf')
    
    for region_code, coords in regions.items():
        distance = calculate_distance(lat, lng, coords['lat'], coords['lng'])
        
        if distance < min_distance:
            min_distance = distance
            user_region = region_code
    
    # Get ALL active businesses, not just from the user's region
    businesses_data = []
    nearby_businesses = []
    regional_businesses = []
    featured_businesses = []
    
    # Get all active businesses
    all_businesses = Business.objects.filter(is_active=True)
    
    # Process all businesses
    for business in all_businesses:
        try:
            # Calculate distance if business has coordinates
            distance = None
            if business.latitude and business.longitude:
                business_lat = float(business.latitude)
                business_lng = float(business.longitude)
                distance = calculate_distance(lat, lng, business_lat, business_lng)
            
            business_data = {
                'id': business.id,
                'name': business.name,
                'description': business.address,
                'region': business.get_region_display() if business.region else None,
                'distance': round(distance, 1) if distance else None,  # Already in km from Haversine formula
                'image': business.cover_image.url if hasattr(business, 'cover_image') and business.cover_image else None,
                'rating': business.rating if hasattr(business, 'rating') else 0,
                'is_featured': business.is_featured,
                'same_region': business.region == user_region,
            }
            
            # Categorize businesses
            if business.is_featured:
                featured_businesses.append(business_data)
                
            if business.region == user_region:
                regional_businesses.append(business_data)
            
            # Add to main list - all businesses sorted by distance
            businesses_data.append(business_data)
        except Exception as e:
            # Skip businesses that cause errors
            continue
    
    # Sort all businesses by distance
    businesses_data = sorted(businesses_data, key=lambda x: x['distance'] if x['distance'] else float('inf'))
    
    # Get businesses in same region, sorted by distance
    regional_businesses = sorted(regional_businesses, key=lambda x: x['distance'] if x['distance'] else float('inf'))
    
    # Sort featured businesses by distance
    featured_businesses = sorted(featured_businesses, key=lambda x: x['distance'] if x['distance'] else float('inf'))
    
    # Limit to nearest 20 businesses and 10 featured businesses
    businesses_data = businesses_data[:20]
    featured_businesses = featured_businesses[:10]
    
    # Get the region display name
    region_display_name = dict(REGION_CHOICES).get(user_region, user_region) if user_region else None
    
    return JsonResponse({
        'all_businesses': businesses_data,
        'regional_businesses': regional_businesses,
        'featured_businesses': featured_businesses,
        'user_region': user_region,
        'region_name': region_display_name
    })



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
        
        # Check if user has a customer profile
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
        
        # Try to get address information from coordinates using reverse geocoding
        import requests
        
        # Using Nominatim for reverse geocoding (free and doesn't require API key)
        # In production, consider using a paid service with better reliability
        nominatim_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
        headers = {
            'User-Agent': 'Mo GasDelivery/1.0'  # Required by Nominatim
        }
        
        response = requests.get(nominatim_url, headers=headers)
        location_data = response.json()
        
        # Extract address components
        address = location_data.get('address', {})
        
        # Create a meaningful address name
        address_name = "Current Location"
        if address.get('road'):
            address_name = address.get('road')
        
        # Create street address
        street = address.get('road', '')
        if address.get('house_number'):
            street = f"{address.get('house_number')} {street}"
        
        # Get area/neighborhood
        area = address.get('suburb') or address.get('neighbourhood') or address.get('district') or ''
        
        # Get city
        city = address.get('city') or address.get('town') or address.get('state') or 'Dar es Salaam'
        
        # Create the address
        new_address = DeliveryAddress.objects.create(
            customer=customer,
            name=address_name,
            street=street or "Unknown Street",
            area=area or "Unknown Area",
            city=city,
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
        return JsonResponse({'success': False, 'error': str(e)})

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
    
    # Get the user's region
    user_region = None
    user_region_name = "Your Area"
    
    # If customer has a default address, use its region
    if customer.addresses.filter(is_default=True).exists():
        default_address = customer.addresses.get(is_default=True)
        user_region = default_address.region
        # Map region code to display name
        region_display_names = {
            'dar_es_salaam': 'Dar es Salaam',
            'arusha': 'Arusha',
            'mwanza': 'Mwanza',
            'zanzibar': 'Zanzibar',
            'dodoma': 'Dodoma',
            'mbeya': 'Mbeya',
            'tanga': 'Tanga',
            'morogoro': 'Morogoro',
            # Add more regions as needed
        }
        user_region_name = region_display_names.get(user_region, user_region.replace('_', ' ').title())
    
    # Example office address (could come from a database in a real implementation)
    office_addresses = {
        'dar_es_salaam': 'Msasani Peninsula, Plot 18, Dar es Salaam',
        'arusha': 'Njiro Complex, Block C, Arusha',
        'mwanza': 'Ilemela District, Mwanza',
        'zanzibar': 'Stone Town, Zanzibar',
        'dodoma': 'Area D, Dodoma',
        # Add more office locations as needed
        'default': 'Main Office, Tanzania'
    }
    
    office_address = office_addresses.get(user_region, office_addresses['default'])
    
    # Calculate total
    total_amount = cart.get_subtotal() + special_delivery_fee
    
    context = {
        'business': business,
        'customer': customer,
        'cart': cart,
        'special_delivery_fee': special_delivery_fee,
        'total_amount': total_amount,
        'user_region_name': user_region_name,
        'office_address': office_address
    }
    
    return render(request, 'customers/featured_checkout.html', context)

@login_required
def place_featured_order(request):
    if request.method == 'POST':
        business_id = request.POST.get('business_id')
        cart_id = request.POST.get('cart_id')
        
        # Get the business and cart
        business = get_object_or_404(Business, id=business_id)
        customer = request.user.customer_profile
        cart = get_object_or_404(Cart, id=cart_id, customer=customer)
        
        # Special delivery fee
        special_delivery_fee = 5000  # Same as in featured_business_checkout
        
        # Create a new order
        order = Order.objects.create(
            customer=customer,
            business=business,
            status='pending',
            delivery_fee=special_delivery_fee,
            subtotal=cart.get_subtotal(),
            total=cart.get_subtotal() + special_delivery_fee,
            special_delivery=True,  # Flag to indicate this is a special delivery order
            order_type='pickup'  # Set to pickup since customer will pick up from the local office
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.price,
                total=cart_item.get_total()
            )
        
        # Clear the cart
        cart.delete()
        
        # Send notification to customer
        # (This would typically involve sending an SMS or email)
        
        messages.success(request, "Your order has been placed successfully! We will notify you when it arrives at our office.")
        return redirect('customers:order_details', order_id=order.id)
    
    # If not POST, redirect to home
    return redirect('customers:home')

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
        if not hasattr(request.user, 'customer_profile'):
            try:
                customer = CustomerProfile.objects.get(user=request.user)
            except CustomerProfile.DoesNotExist:
                customer = CustomerProfile.objects.create(
                    user=request.user,
                    phone_number=f"temp_{request.user.id}"
                )
        else:
            customer = request.user.customer_profile
        
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
        cart_items = cart.items.all()
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        cart_count = sum(item.quantity for item in cart_items)
        
        # Calculate delivery fee
        delivery_fee = Decimal('2000')  # Default fee
        if hasattr(customer, 'default_address') and customer.default_address and cart.business:
            delivery_fee = calculate_delivery_fee(cart.business, customer.default_address)
        
        total = subtotal + delivery_fee
        
        # Return success response with updated data
        return JsonResponse({
            'success': True,
            'message': 'Cart updated successfully',
            'item_subtotal': float(cart_item.product.price * cart_item.quantity),
            'subtotal': float(subtotal),
            'delivery_fee': float(delivery_fee),
            'total': float(total),
            'cart_count': cart_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error updating cart: {str(e)}'})
