import csv
from datetime import timedelta
import re
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
import csv
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
import uuid
from datetime import datetime, timedelta
from orders.models import Order, OrderAssignmentGroup
from riders.models import Rider
from riders.utils import get_nearby_riders  # Import only what we need
from django.contrib.auth.views import LoginView
from business.models import Business
from orders.models import Order
from .models import  REGION_CHOICES, CustomUser, Kijiwe, UserProfile
from .serializers import  KijiweSerializer
from .forms import KijiweForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm 
from django.contrib.auth import logout # or wherever your UserProfile is defined

# Logout view
def logout_view(request):
    logout(request)
    return redirect('operations:login')



def dashboard_register(request):
    if request.method == 'POST':
        # Get form data
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        region = request.POST.get('region')
        
        # Basic validation
        if not phone or not re.match(r'^\d{9,12}$', phone):
            messages.error(request, "Please enter a valid phone number.")
        elif not email:
            messages.error(request, "Email is required.")
        elif not region:
            messages.error(request, "Please select a region.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif len(password1) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            try:
                # Normalize phone number
                cleaned_phone = ''.join(filter(str.isdigit, phone))
                if not cleaned_phone.startswith('255'):
                    if cleaned_phone.startswith('0'):
                        cleaned_phone = '255' + cleaned_phone[1:]
                    elif cleaned_phone.startswith('7'):
                        cleaned_phone = '255' + cleaned_phone
                
                # Check if user exists and update role if needed
                try:
                    existing_user = CustomUser.objects.get(phone=cleaned_phone)
                    
                    # Update the existing user to also have operations role
                    existing_user.role = 'operations'
                    existing_user.email = email
                    existing_user.region = region
                    
                    # Only update password if provided
                    if password1:
                        existing_user.set_password(password1)
                    
                    existing_user.save()
                    
                    # Create UserProfile if it doesn't exist
                    UserProfile.objects.get_or_create(
                        user=existing_user,
                        defaults={
                            'region': region,
                            # Add other UserProfile fields as needed
                        }
                    )
                    
                    messages.success(request, "Account updated with operations access.")
                    return redirect('operations:login')
                
                except CustomUser.DoesNotExist:
                    # Create new user
                    user = CustomUser.objects.create_user(
                        phone=cleaned_phone,
                        email=email,
                        password=password1,
                        region=region,
                        role='operations'
                    )
                    
                    # Create UserProfile
                    UserProfile.objects.create(
                        user=user,
                        region=region,
                        # Add other UserProfile fields as needed
                    )
                    
                    messages.success(request, "Account created successfully. You can now log in.")
                    return redirect('operations:login')
                    
            except Exception as e:
                messages.error(request, f"Error processing account: {str(e)}")
    
    # Define regions list
    regions = REGION_CHOICES
    return render(request, 'operations/register.html', {'regions': REGION_CHOICES})

def dashboard_login(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        # Print raw input for debugging
        print(f"Raw phone input: {phone}")
        
        # Clean and normalize phone number
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        
        # Apply the same logic as in your CustomUserManager
        if not cleaned_phone.startswith('255'):
            if cleaned_phone.startswith('0'):
                cleaned_phone = '255' + cleaned_phone[1:]
            elif cleaned_phone.startswith('7'):
                cleaned_phone = '255' + cleaned_phone
        
        # Print cleaned phone for debugging
        print(f"Cleaned phone: {cleaned_phone}")
        
        # Authenticate with the cleaned phone number
        user = authenticate(request, username=cleaned_phone, password=password)
        
        if user is not None:
            login(request, user)
            # Check if user has operations role
            if user.role == 'operations':
                return redirect('operations:dashboard')
            else:
                messages.error(request, "Your account doesn't have the required permissions to access operations dashboard.")
                logout(request)
        else:
            # For debugging, try to find if the user exists with this phone
            try:
                user_exists = CustomUser.objects.filter(phone=cleaned_phone).exists()
                print(f"User exists with this phone? {user_exists}")
                if user_exists:
                    print("User exists but password is incorrect")
                else:
                    print("No user found with this phone number")
            except Exception as e:
                print(f"Error checking user: {str(e)}")
                
            messages.error(request, "Invalid phone number or password.")
        
    return render(request, 'operations/login.html')

@login_required
def dashboard(request):
    """Render the dashboard with pending and active orders"""
    try:
        # Try to get the user profile
        user_profile = UserProfile.objects.get(user=request.user)
        user_region = user_profile.region
        
        today = timezone.now().date()
        
        pending_orders = Order.objects.filter(
        status__in=['pending', 'confirmed'],
        business__region=user_region
            ).order_by('-created_at')
        
        # Query active orders (orders in progress)
        active_orders = Order.objects.filter(
            status__in=['assigned', 'preparing', 'ready', 'in_transit'],
            business__region=user_region
        ).order_by('-updated_at')
        
        context = {
            'pending_orders': pending_orders,
            'active_orders': active_orders,
            'current_region': user_region
        }
        
        return render(request, 'operations/dashboard.html', context)
    
    except UserProfile.DoesNotExist:
        # Log the user out
        messages.error(request, "Your account doesn't have the required profile to access the dashboard. Please contact an administrator.")
        return redirect('operations:logout')
    
@login_required
def order_list(request):
    """View for listing all orders"""
    orders = Order.objects.all().order_by('-created_at')
    context = {
        'orders': orders
    }
    return render(request, 'operations/order_list.html', context)


@login_required
def kijiwe_list(request):
    """View for listing all kijiwe locations"""
    kijiwe_locations = Kijiwe.objects.all().order_by('name')
    form = KijiweForm()
    context = {
        'kijiwe_locations': kijiwe_locations,
        'form': form
    }
    return render(request, 'operations/kijiwe_list.html', context)

@login_required
def kijiwe_detail(request, pk):
    """View for showing kijiwe details"""
    kijiwe = get_object_or_404(Kijiwe, pk=pk)
    context = {
        'kijiwe': kijiwe
    }
    return render(request, 'operations/kijiwe_detail.html', context)

@login_required
def kijiwe_create(request):
    """View for creating a new kijiwe location"""
    if request.method == 'POST':
        form = KijiweForm(request.POST)
        if form.is_valid():
            kijiwe = form.save()
            messages.success(request, 'Kijiwe location created successfully.')
            return redirect('operations:kijiwe_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('operations:kijiwe_list')
    return redirect('operations:kijiwe_list')


@api_view(['GET'])
@permission_classes([AllowAny])  # Allows public access
def kijiwe_by_region_api(request):
    """Fetch Kijiwe locations based on the selected region"""
    region = request.GET.get('region')

    if not region:
        return Response({"error": "Region parameter is required"}, status=400)

    kijiwe_locations = Kijiwe.objects.filter(region=region).order_by('name')
    
    if not kijiwe_locations.exists():
        return Response({"message": "No Kijiwe found for this region"}, status=200)

    serializer = KijiweSerializer(kijiwe_locations, many=True)
    return Response(serializer.data)

@login_required
def order_history_view(request):
    """Renders the order history page."""
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'operations/order_history.html', {
        'region': user_profile.region
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_by_tracking(request, order_number):
    """Get order details by tracking number."""
    try:
        order = Order.objects.get(order_number=order_number)
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=404)

@login_required
def order_history_api(request):
    """API endpoint for fetching order history with filters."""
    try:
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        status = request.GET.get('status')
        search = request.GET.get('search')
        
        # Base query
        orders = Order.objects.all().order_by('-created_at')
        
        # Apply filters
        if start_date and end_date:
            orders = orders.filter(created_at__date__range=[start_date, end_date])
        
        if status and status != 'all':
            orders = orders.filter(status=status)
            
        if search:
            orders = orders.filter(
                Q(order_number__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search) |
                Q(delivery_location__icontains=search)
            )
        
        # Prepare response data
        data = []
        for order in orders:
            data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'delivery_location': order.delivery_location,
                'status': order.get_status_display(),
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'total_amount': float(order.total_amount)
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

@login_required
def export_orders_csv(request):
    """Export orders to CSV based on filters."""
    try:
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        status = request.GET.get('status')
        
        # Base query
        orders = Order.objects.all().order_by('-created_at')
        
        # Apply filters
        if start_date and end_date:
            orders = orders.filter(created_at__date__range=[start_date, end_date])
        
        if status and status != 'all':
            orders = orders.filter(status=status)
        
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
        
        # Create CSV writer
        writer = csv.writer(response)
        writer.writerow([
            'Tracking Number',
            'Customer Name',
            'Phone',
            'Location',
            'Status',
            'Created At',
            'Total Amount'
        ])
        
        # Write data
        for order in orders:
            writer.writerow([
                order.order_number,
                order.customer_name,
                order.customer_phone,
                order.delivery_location,
                order.get_status_display(),
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                float(order.total_amount)
            ])
        
        return response
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# API Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list_api(request):
    """API endpoint for listing orders"""
    orders = Order.objects.all().order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kijiwe_list_api(request):
    """API endpoint for listing kijiwe locations"""
    kijiwe_locations = Kijiwe.objects.all().order_by('name')
    serializer = KijiweSerializer(kijiwe_locations, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kijiwe_detail_api(request, pk):
    """API endpoint for kijiwe details"""
    kijiwe = get_object_or_404(Kijiwe, pk=pk)
    serializer = KijiweSerializer(kijiwe)
    return Response(serializer.data)



class OperationsLoginView(LoginView):
    template_name = 'operations/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('operations:dashboard')


@login_required
def order_history(request):
    """Display order history for the operations dashboard"""
    try:
        # Get user profile and region
        user_profile = UserProfile.objects.get(user=request.user)
        user_region = user_profile.region
        
        # Get completed and cancelled orders
        completed_orders = Order.objects.filter(
            status__in=['delivered', 'cancelled'],
            business__region=user_region
        ).order_by('-updated_at')
        
        # Optional: Add date filtering
        date_filter = request.GET.get('date_filter', 'all')
        
        if date_filter == 'today':
            today = timezone.now().date()
            completed_orders = completed_orders.filter(updated_at__date=today)
        elif date_filter == 'week':
            week_ago = timezone.now().date() - timedelta(days=7)
            completed_orders = completed_orders.filter(updated_at__date__gte=week_ago)
        elif date_filter == 'month':
            month_ago = timezone.now().date() - timedelta(days=30)
            completed_orders = completed_orders.filter(updated_at__date__gte=month_ago)
        
        return render(request, 'operations/order_history.html', {
            'orders': completed_orders,
            'current_region': user_region,
            'date_filter': date_filter
        })
        
    except UserProfile.DoesNotExist:
        messages.error(request, "Your account doesn't have the required profile to access this page.")
        return redirect('operations:logout')

@login_required
def riders_list(request):
    """Display and manage riders for the operations dashboard"""
    try:
        # Get user profile and region
        user_profile = UserProfile.objects.get(user=request.user)
        user_region = user_profile.region
        
        # Get all riders in the user's region
        riders = Rider.objects.filter(region=user_region).order_by('first_name', 'last_name')
        
        # Optional: Add search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            riders = riders.filter(
                Q(phone_number__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        return render(request, 'operations/riders_list.html', {
            'riders': riders,
            'region': user_region,
            'search_query': search_query
        })
    
    except UserProfile.DoesNotExist:
        messages.error(request, "Your account doesn't have the required profile to access this page.")
        return redirect('operations:logout')
    
    
@login_required
def riders_api(request):
    """API endpoint for riders data"""
    try:
        # Get user profile and region
        user_profile = UserProfile.objects.get(user=request.user)
        user_region = user_profile.region
        
        # Get all riders in the user's region
        riders = Rider.objects.filter(region=user_region).order_by('first_name', 'last_name')
        
        # Optional: Add search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            riders = riders.filter(
                Q(phone_number__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Convert riders queryset to JSON-serializable format
        riders_data = []
        for rider in riders:
            # Create base data dictionary with fields matching your model
            rider_data = {
                'user__first_name': rider.first_name,
                'user__last_name': rider.last_name,
                'phone_number': rider.phone_number,
                'kijiwe': rider.kijiwe.name if rider.kijiwe else 'N/A',
                # Use is_available instead of is_active
                'is_active': rider.is_available,
                'is_available': rider.is_available,
                'last_active': rider.updated_at.isoformat() if rider.updated_at else None,
                'created_at': rider.created_at.isoformat() if rider.created_at else None,
                'total_deliveries': getattr(rider, 'total_deliveries', 0),
                'deliveries_today': getattr(rider, 'deliveries_today', 0),
                'region': rider.region,
                'rating': getattr(rider, 'rating', None),
                'can_receive_orders': rider.can_receive_orders(),
                'penalties': rider.penalties,
            }
            
            # Add current order if available
            try:
                current_order = Order.objects.filter(rider=rider, status__in=['ASSIGNED', 'PICKED_UP', 'IN_PROGRESS']).first()
                if current_order:
                    rider_data['current_order'] = {
                        'tracking_number': current_order.tracking_number,
                        'status': current_order.status,
                        'assigned_at': current_order.assigned_at.isoformat() if current_order.assigned_at else None
                    }
                else:
                    rider_data['current_order'] = None
            except:
                rider_data['current_order'] = None
            
            # Add penalty history if available
            try:
                penalties = []
                # Check if there's a related penalty model - adjust this based on your actual model structure
                penalty_records = getattr(rider, 'penalty_records', [])
                if hasattr(penalty_records, 'all'):
                    for penalty in penalty_records.all():
                        penalties.append({
                            'type': getattr(penalty, 'type', 'Penalty'),
                            'reason': getattr(penalty, 'reason', f'Penalty Count: {rider.penalties}'),
                            'created_at': penalty.created_at.isoformat() if hasattr(penalty, 'created_at') and penalty.created_at else None
                        })
                
                # If no penalty records but rider has penalties, create a generic entry
                if not penalties and rider.penalties > 0:
                    penalties.append({
                        'type': 'System Penalty',
                        'reason': f'Rider has {rider.penalties} penalties',
                        'created_at': rider.updated_at.isoformat() if rider.updated_at else None
                    })
                
                rider_data['penalties'] = penalties
            except Exception as e:
                rider_data['penalties'] = []
            
            riders_data.append(rider_data)
        
        return JsonResponse({
            'success': True,
            'riders': riders_data
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': "Your account doesn't have the required profile to access this page."
        }, status=403)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def business_list(request):
    """Display and manage businesses for the operations dashboard"""
    try:
        # Get user profile and region
        user_profile = UserProfile.objects.get(user=request.user)
        user_region = user_profile.region
        
        # Get all businesses in the user's region
        businesses = Business.objects.filter(
            region=user_region
        ).order_by('name')
        
        # Optional: Add search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            businesses = businesses.filter(
                Q(name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(address__icontains=search_query)
            )
        
        return render(request, 'operations/business_list.html', {
            'businesses': businesses,
            'current_region': user_region,
            'search_query': search_query
        })
        
    except UserProfile.DoesNotExist:
        messages.error(request, "Your account doesn't have the required profile to access this page.")
        return redirect('operations:logout')




def dashboard_data(request):
    """
    API endpoint to provide all data needed for the operations dashboard.
    Returns counts, active, pending, and completed orders.
    """
    today = timezone.now().date()
    
    # Get counts
    total_orders_today = Order.objects.filter(created_at__date=today).count()
    active_riders_count = Rider.objects.filter(is_available=True).count()
    
    # Get active orders (assigned, preparing, ready, or in_transit)
    active_orders = Order.objects.filter(
        status__in=['assigned', 'preparing', 'ready', 'in_transit']
    ).select_related(
        'business', 'pickup_location'
    ).order_by('-created_at')
    
    # Get pending orders
    pending_orders = Order.objects.filter(
        status='pending'
    ).select_related(
        'business', 'pickup_location'
    ).order_by('-created_at')
    
    # Get completed (delivered) orders
    completed_orders = Order.objects.filter(
        status='delivered'
    ).select_related(
        'business', 'pickup_location'
    ).order_by('-created_at')[:50]  # Limit to most recent 50
    
    # Format the active orders for the response
    active_orders_data = []
    for order in active_orders:
        # Find the active assignment group for this order
        assignment_group = OrderAssignmentGroup.objects.filter(
            order=order,
            is_active=True
        ).prefetch_related('riders').first()
        
        # Get the rider info if available
        rider = None
        if assignment_group and assignment_group.riders.exists():
            rider = assignment_group.riders.first()
        
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'business__name': order.business.name if order.business else (order.pickup_location.name if order.pickup_location else "Unknown"),
            'delivery_location': order.delivery_location,
            'price': float(order.subtotal) if order.subtotal else 0,
            'delivery_fee': float(order.delivery_fee) if order.delivery_fee else 0,
            'total_amount': float(order.total) if order.total else 0,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
        }
        
        # Add rider info if available
        if rider:
            order_data.update({
                'rider__user__first_name': rider.first_name,
                'rider__user__last_name': rider.last_name,
                'rider__phone_number': rider.phone_number,
            })
        
        active_orders_data.append(order_data)
    
    # Format the pending orders
    pending_orders_data = []
    for order in pending_orders:
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'business__name': order.business.name if order.business else (order.pickup_location.name if order.pickup_location else "Unknown"),
            'delivery_location': order.delivery_location,
            'price': float(order.subtotal) if order.subtotal else 0,
            'delivery_fee': float(order.delivery_fee) if order.delivery_fee else 0,
            'total_amount': float(order.total) if order.total else 0,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
        }
        
        # Check if there's already an active assignment group
        has_active_group = OrderAssignmentGroup.objects.filter(
            order=order,
            is_active=True
        ).exists()
        
        if not has_active_group:
            # We'll fetch nearby riders on demand when needed
            order_data['has_nearest_rider'] = order.pickup_latitude is not None and order.pickup_longitude is not None
        else:
            order_data['has_active_assignment'] = True
        
        pending_orders_data.append(order_data)
    
    # Format the completed orders
    completed_orders_data = []
    for order in completed_orders:
        # Find the assignment group for this completed order
        assignment_group = OrderAssignmentGroup.objects.filter(
            order=order,
            is_active=False  # Completed orders should have inactive groups
        ).prefetch_related('riders').first()
        
        # Get the rider info if available
        rider = None
        if assignment_group and assignment_group.riders.exists():
            rider = assignment_group.riders.first()
        
        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'business__name': order.business.name if order.business else (order.pickup_location.name if order.pickup_location else "Unknown"),
            'delivery_location': order.delivery_location,
            'price': float(order.subtotal) if order.subtotal else 0,
            'delivery_fee': float(order.delivery_fee) if order.delivery_fee else 0,
            'total_amount': float(order.total) if order.total else 0,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
        }
        
        # Add rider info if available
        if rider:
            order_data.update({
                'rider__user__first_name': rider.first_name,
                'rider__user__last_name': rider.last_name,
                'rider__phone_number': rider.phone_number,
            })
        
        completed_orders_data.append(order_data)
    
    # Prepare the final response
    response = {
        'success': True,
        'total_orders_today': total_orders_today,
        'active_riders_count': active_riders_count,
        'active_orders': active_orders_data,
        'pending_orders': pending_orders_data,
        'completed_orders': completed_orders_data
    }
    
    return JsonResponse(response)

def order_detail(request, order_uuid):
    """
    API endpoint to get detailed information about a specific order using UUID.
    """
    try:
        # Find the order by UUID instead of ID
        order = Order.objects.get(uuid_tracking=order_uuid)
        
        # Get business name from either business or pickup_location
        business_name = "Unknown"
        if order.business:
            business_name = order.business.name
        elif order.pickup_location:
            business_name = order.pickup_location.name
        
        # Prepare order data
        order_data = {
            'id': order.id,
            'uuid': str(order.uuid_tracking),
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'business__name': business_name,
            'delivery_location': order.delivery_location,
            'price': float(order.subtotal) if order.subtotal else 0,
            'delivery_fee': float(order.delivery_fee) if order.delivery_fee else 0,
            'total_amount': float(order.total) if order.total else 0,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
        }
        
        # Check if there's an active assignment group
        active_group = OrderAssignmentGroup.objects.filter(
            order=order,
            is_active=True
        ).first()
        
        if active_group:
            order_data['has_active_assignment'] = True
            order_data['assignment_group_id'] = str(active_group.group_id)
            
            # If there are riders in the group, include their info
            if active_group.riders.exists():
                riders_data = []
                for rider in active_group.riders.all():
                    riders_data.append({
                        'id': rider.id,
                        'name': f"{rider.first_name} {rider.last_name}",
                        'phone': rider.phone_number
                    })
                order_data['assigned_riders'] = riders_data
        
        # Include coordinates if available
        if order.pickup_latitude and order.pickup_longitude:
            order_data['pickup_coordinates'] = {
                'latitude': float(order.pickup_latitude),
                'longitude': float(order.pickup_longitude)
            }
        
        if order.delivery_latitude and order.delivery_longitude:
            order_data['delivery_coordinates'] = {
                'latitude': float(order.delivery_latitude),
                'longitude': float(order.delivery_longitude)
            }
        
        return JsonResponse({
            'success': True,
            'order': order_data
        })
            
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Order with UUID {order_uuid} not found'
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


        
        
def assign_rider(request, order_uuid, rider_id):
    """
    API endpoint to assign a rider to an order using UUID instead of ID.
    Creates an OrderAssignmentGroup and adds the rider to it.
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405)
    
    try:
        # Find the order by UUID instead of ID
        order = Order.objects.get(uuid_tracking=order_uuid)
        rider = Rider.objects.get(id=rider_id)
        
        # Check if order can be assigned
        assignable_statuses = ['pending', 'confirmed']
        if order.status.lower() not in assignable_statuses:
            return JsonResponse({
                'success': False,
                'error': f'Order cannot be assigned. Current status: {order.status}. Must be one of: {", ".join(assignable_statuses)}'
            }, status=400)
        
        # Check if rider is available
        if not rider.is_available:
            return JsonResponse({
                'success': False,
                'error': 'Rider is not available'
            }, status=400)
        
        # Check if there's already an active assignment group
        existing_group = OrderAssignmentGroup.objects.filter(
            order=order,
            is_active=True
        ).first()
        
        if existing_group:
            # Add the rider to the existing group if not already in it
            if rider not in existing_group.riders.all():
                existing_group.riders.add(rider)
                
            assignment_group = existing_group
        else:
            # Create assignment group
            assignment_group = OrderAssignmentGroup.objects.create(
                order=order,
                is_active=True
            )
            assignment_group.riders.add(rider)
        
        # Update order status
        order.status = 'assigned'
        order.save()
        
        # Get the distance between rider and order if coordinates are available
        distance_info = ""
        if (rider.latitude and rider.longitude and 
            order.pickup_latitude and order.pickup_longitude):
            try:
                from riders.utils import calculate_distance
                distance = calculate_distance(
                    float(rider.latitude), float(rider.longitude),
                    float(order.pickup_latitude), float(order.pickup_longitude)
                )
                # Convert from meters to kilometers
                distance_km = distance / 1000
                distance_info = f" (Distance: {distance_km:.1f}km)"
            except Exception:
                pass
        
        return JsonResponse({
            'success': True,
            'message': f'Rider {rider.first_name} {rider.last_name} assigned to order #{order.order_number}{distance_info}',
            'group_id': str(assignment_group.group_id),
            'order_id': order.id,
            'order_uuid': str(order.uuid_tracking),
            'order_number': order.order_number,
            'rider_id': rider.id,
            'rider_name': f"{rider.first_name} {rider.last_name}",
            'rider_phone': rider.phone_number
        })
            
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Order with UUID {order_uuid} not found'
        }, status=404)
    except Rider.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Rider not found'
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def assign_multiple_riders(request, order_id):
    """
    API endpoint to assign multiple riders to an order at once.
    Creates an OrderAssignmentGroup and adds all specified riders to it.
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        rider_ids = data.get('rider_ids', [])
        
        if not rider_ids:
            return JsonResponse({
                'success': False,
                'error': 'No rider IDs provided'
            }, status=400)
        
        order = Order.objects.get(id=order_id)
        
        # Check if order can be assigned
        if order.status != 'pending' and order.status != 'confirmed':
            return JsonResponse({
                'success': False,
                'error': f'Order cannot be assigned. Current status: {order.status}'
            }, status=400)
        
        # Check if there's already an active assignment group
        existing_group = OrderAssignmentGroup.objects.filter(
            order=order,
            is_active=True
        ).first()
        
        if existing_group:
            # Use the existing group
            assignment_group = existing_group
        else:
            # Create a new assignment group
            assignment_group = OrderAssignmentGroup.objects.create(
                order=order,
                is_active=True
            )
        
        # Add each rider to the group
        added_riders = []
        for rider_id in rider_ids:
            try:
                rider = Rider.objects.get(id=rider_id)
                
                # Only add available riders
                if rider.is_available:
                    assignment_group.riders.add(rider)
                    added_riders.append({
                        'id': rider.id,
                        'name': f"{rider.first_name} {rider.last_name}"
                    })
            except Rider.DoesNotExist:
                continue
        
        # Only update order status if riders were added
        if added_riders:
            order.status = 'assigned'
            order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{len(added_riders)} riders assigned to order #{order.order_number}',
            'added_riders': added_riders,
            'group_id': str(assignment_group.group_id)
        })
            
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Order not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        

def order_details(request, order_id):
    """
    Fetch order details with a specific response structure
    
    Args:
        request: HTTP request object
        order_id: Unique identifier for the order
    
    Returns:
        JsonResponse with order details in expected format
    """
    try:
        # Fetch the order, return 404 if not found
        order = get_object_or_404(Order, id=order_id)
        
        # Prepare order data in the expected structure
        order_data = {
            'success': True,
            'order': {
                'id': order.id,
                'order_number': order.order_number,  # Assuming you have this field
                'customer_name': order.customer_name,
                'business__name': order.business.name if order.business else '',  # Adjust based on your model
                'delivery_location': order.delivery_location,
                'total_amount': order.total,
                'pickup_latitude': str(order.pickup_latitude),
                'pickup_longitude': str(order.pickup_longitude),
                'created_at': order.created_at.isoformat() if order.created_at else None,
            }
        }
        
        return JsonResponse(order_data)
    
    except Exception as e:
        # Handle any unexpected errors
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
        
def nearby_riders(request, order_id):
    """
    API endpoint to find available riders near a specific order.
    """
    try:
        # Find the order 
        order = get_object_or_404(Order, id=order_id)
        
        # Check if pickup coordinates are available
        if not order.pickup_latitude or not order.pickup_longitude:
            return JsonResponse({
                'success': False,
                'error': 'Order pickup location coordinates not available'
            }, status=400)
        
        # Find available riders within 500 meters (0.5 km)
        nearby_riders_data = get_nearby_riders(
            latitude=order.pickup_latitude, 
            longitude=order.pickup_longitude, 
            max_distance=0.5,  # 500 meters
            is_available=True  # Only get available riders
        )
        
        # If no available riders found within 500m, try a wider radius of 2km
        if not nearby_riders_data:
            nearby_riders_data = get_nearby_riders(
                latitude=order.pickup_latitude, 
                longitude=order.pickup_longitude, 
                max_distance=2,  # 2 kilometers
                is_available=True  # Only get available riders
            )
        
        # Format the rider data for response
        riders_list = []
        for item in nearby_riders_data:
            rider = item['rider']
            riders_list.append({
                'id': rider.id,
                'first_name': rider.first_name,
                'last_name': rider.last_name,
                'phone_number': rider.phone_number,
                'distance': item['distance'],
                'distance_text': f"{item['distance']*1000:.0f}m" if item['distance'] < 1 else f"{item['distance']:.1f}km",
                'kijiwe': rider.kijiwe.name if hasattr(rider, 'kijiwe') and rider.kijiwe else None
            })
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number,
            'pickup_location': {
                'latitude': float(order.pickup_latitude),
                'longitude': float(order.pickup_longitude),
                'address': order.pickup_location.name if order.pickup_location else (
                    order.business.name if order.business else "Unknown location"
                )
            },
            'nearby_riders_count': len(riders_list),
            'nearby_riders': riders_list
        })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def get_nearby_riders(latitude, longitude, max_distance, is_available=True):
    """
    Find riders within a specified distance from a given location.
    
    Args:
    - latitude: Latitude of the reference point
    - longitude: Longitude of the reference point
    - max_distance: Maximum distance in kilometers to search
    - is_available: Filter for only available riders
    
    Returns:
    List of nearby riders with their distances
    """
    from riders.models import Rider  # Import here to avoid circular imports
    
    # Base queryset with availability filter
    riders_query = Rider.objects.filter(is_available=is_available)
    
    nearby_riders = []
    
    for rider in riders_query:
        # Skip riders without current location
        if not (rider.latitude and rider.longitude):
            continue
        
        # Calculate distance using Haversine formula
        distance = haversine_distance(
            float(latitude), 
            float(longitude), 
            float(rider.latitude), 
            float(rider.longitude)
        )
        
        # Check if rider is within max distance
        if distance <= max_distance:
            nearby_riders.append({
                'rider': rider,
                'distance': distance
            })
    
    # Sort riders by distance
    return sorted(nearby_riders, key=lambda x: x['distance'])

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    from math import radians, sin, cos, sqrt, atan2
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Radius of earth in kilometers
    radius = 6371
    
    return radius * c



@login_required
def rider_completed_orders_api(request, rider_id=None):
    """API endpoint for rider's completed orders"""
    try:
        # Either get the specific rider or the logged-in rider
        if rider_id and request.user.is_staff:  # Only staff can view other riders' orders
            rider = get_object_or_404(Rider, id=rider_id)
        else:
            rider = get_object_or_404(Rider, user=request.user)
        
        # Get completed orders
        completed_orders = Order.objects.filter(
            assignment_groups__riders=rider,
            status='delivered'
        )
        
        # Get counts for different time periods
        today = timezone.now().date()
        today_count = completed_orders.filter(updated_at__date=today).count()
        
        # Get basic details for the last 10 completed orders
        recent_orders = []
        for order in completed_orders.order_by('-updated_at')[:10]:
            recent_orders.append({
                'order_number': order.order_number,
                'completed_at': order.updated_at,
                'delivery_fee': float(order.delivery_fee) if order.delivery_fee else 0,
                # Add other relevant order details here
            })
        
        return JsonResponse({
            'success': True,
            'total_deliveries': completed_orders.count(),
            'today_deliveries': today_count,
            'recent_completed_orders': recent_orders
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rider_stats_api(request, rider_id=None):
    """
    API endpoint for operations to get rider stats including total deliveries
    """
    if not rider_id:
        return JsonResponse({
            'success': False,
            'error': 'Rider ID is required'
        }, status=400)
        
    try:
        rider = Rider.objects.get(id=rider_id)
        
        # Get completed/delivered orders
        completed_orders = Order.objects.filter(
            assignment_groups__riders=rider,
            status='delivered'  # or whatever status represents completed deliveries
        )
        
        total_deliveries = completed_orders.count()
        
        # You can add more stats here as needed
        
        return JsonResponse({
            'success': True,
            'rider_id': rider_id,
            'total_deliveries': total_deliveries,
            # Add any other stats you want to include
        })
    except Rider.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Rider not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)