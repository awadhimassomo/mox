from venv import logger
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from riders.models import Rider
from .models import Order, CustomerProfile, OrderAssignmentGroup

def incoming_orders(request):
    """Retrieve all pending orders."""
    orders = Order.objects.filter(status="pending").values()
    return JsonResponse({"orders": list(orders)})

@login_required
def orders(request):
    """Display all orders for the logged-in customer"""
    # Get or create customer profile
    customer, created = CustomerProfile.objects.get_or_create(user=request.user)
    orders_list = Order.objects.filter(customer=customer).order_by('-created_at')
    
    context = {
        'orders': orders_list
    }
    return render(request, 'orders/orders.html', context)

@login_required
def order_detail(request, order_id):
    """Display details of a specific order"""
    order = get_object_or_404(Order, id=order_id)
    
    # Ensure user owns this order
    if order.customer.user != request.user:
        messages.error(request, "You don't have permission to view this order.")
        return redirect('orders:orders')
    
    context = {
        'order': order
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def complete_order_api(request, order_id):
    """API endpoint to mark an order as completed"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        rider = Rider.objects.get(user=request.user)
        order = Order.objects.get(id=order_id)
        
        # Check if this rider is assigned to this order
        assignment = OrderAssignmentGroup.objects.filter(
            order=order,
            riders=rider,
            is_active=True
        ).first()
        
        if not assignment:
            return JsonResponse({
                'success': False,
                'error': 'You are not assigned to this order'
            }, status=403)
        
        # Update order status to completed
        order.status = 'delivered'
        order.completed_at = timezone.now()
        order.completed_by = rider
        order.save()
        
        logger.info(f"Order #{order_id} marked as completed by rider {rider.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Order marked as completed successfully'
        })
        
    except Rider.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Rider not found'
        }, status=404)
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Order not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error completing order {order_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error completing order: {str(e)}'
        }, status=500)
