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
            orders=order,
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
