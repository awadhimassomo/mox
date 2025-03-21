"""
Script to assign specific orders to a rider via OrderAssignmentGroup
Run this from the Django shell:
python manage.py shell < assign_orders.py

Or for more direct control, run it with your rider ID like:
python manage.py shell -c "rider_id=1; exec(open('assign_orders.py').read())"
(replace 1 with your rider's ID)
"""

from orders.models import Order, OrderAssignmentGroup
from riders.models import Rider
import sys

# Define the order numbers you want to assign (from your screenshot)
order_numbers = [
    'MO-2503180636F9PL',  # Pending order
    'MO-2503180619FV4B'   # Processing order
]

# Get the rider - check if rider_id was provided from command line
if 'rider_id' not in globals():
    # No rider_id provided in command, attempt to get the first available rider
    rider = Rider.objects.first()
    if rider:
        rider_id = rider.id
        print(f"Using first available rider: ID {rider_id}")
    else:
        print("No riders found in the system!")
        sys.exit(1)

try:
    # Get the rider
    rider = Rider.objects.get(id=rider_id)
    print(f"Found rider: {rider.id}, Name: {rider.first_name} {rider.last_name}")
    
    # Get the orders
    for order_number in order_numbers:
        try:
            order = Order.objects.get(order_number=order_number)
            print(f"Found order: {order.order_number} (Status: {order.status})")
            
            # Check if order already has an assignment group
            existing_group = OrderAssignmentGroup.objects.filter(order=order, is_active=True).first()
            
            if existing_group:
                print(f"Order {order.order_number} already has an assignment group")
                
                # Add rider to existing group if not already in it
                if rider not in existing_group.riders.all():
                    existing_group.riders.add(rider)
                    print(f"Added rider {rider.id} to existing assignment group")
                else:
                    print(f"Rider {rider.id} already in assignment group")
            else:
                # Create new assignment group
                group = OrderAssignmentGroup.objects.create(
                    order=order,
                    is_active=True
                )
                group.riders.add(rider)
                print(f"Created new assignment group for order {order.order_number} and added rider {rider.id}")
        
        except Order.DoesNotExist:
            print(f"Order {order_number} not found")
        except Exception as e:
            print(f"Error processing order {order_number}: {str(e)}")
    
    print("\nAssignment complete. Check the rider dashboard to see if orders appear now.")
except Rider.DoesNotExist:
    print(f"Rider with ID {rider_id} not found")
except Exception as e:
    print(f"Error: {str(e)}")
