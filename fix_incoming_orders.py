"""
This is a Django shell script to fix orders assignment.
Run it from the Django shell with:

python manage.py shell < fix_incoming_orders.py

It will show detailed information about existing orders and riders, and
create OrderAssignmentGroup entries for orders that need them.
"""

from orders.models import Order, OrderAssignmentGroup
from riders.models import Rider
from django.db.models import Q

# Print all riders for reference
print("===== AVAILABLE RIDERS =====")
riders = Rider.objects.all()
if not riders:
    print("No riders found in the system!")
else:
    for r in riders:
        print(f"ID: {r.id}, Name: {r.first_name} {r.last_name}, Phone: {r.phone_number}")

# Print all recent orders
print("\n===== RECENT ORDERS =====")
orders = Order.objects.filter(
    ~Q(status__in=['delivered', 'cancelled'])
).order_by('-created_at')[:10]  # Get 10 most recent undelivered/uncancelled orders

if not orders:
    print("No active orders found!")
else:
    for order in orders:
        # Check assignment status
        assignment_groups = OrderAssignmentGroup.objects.filter(order=order)
        assigned_riders = []
        for group in assignment_groups:
            riders_list = list(group.riders.values_list('id', flat=True))
            assigned_riders.extend(riders_list)
        
        print(f"Order: {order.order_number}")
        print(f"  - Status: {order.status}")
        print(f"  - Created: {order.created_at}")
        print(f"  - Business: {order.business.name if order.business else 'None'}")
        print(f"  - Assignment Groups: {assignment_groups.count()}")
        print(f"  - Assigned to riders: {assigned_riders}")
        print("")

# Fix specific orders from the screenshot
target_orders = [
    'MO-2503180636F9PL',  # Pending order
    'MO-2503180619FV4B'   # Processing order
]

print("\n===== FIXING TARGET ORDERS =====")
# Get the first rider (or let user specify one)
if riders:
    # Use first rider for simplicity
    rider = riders.first()
    print(f"Using rider: ID {rider.id}, Name: {rider.first_name} {rider.last_name}")
    
    # Assign orders to this rider
    for order_number in target_orders:
        try:
            order = Order.objects.get(order_number=order_number)
            print(f"Found order: {order.order_number} (Status: {order.status})")
            
            # Create assignment group if needed
            group, created = OrderAssignmentGroup.objects.get_or_create(
                order=order,
                defaults={'is_active': True}
            )
            
            # Add rider to group
            if rider not in group.riders.all():
                group.riders.add(rider)
                print(f"✅ Added rider {rider.id} to assignment group for order {order.order_number}")
            else:
                print(f"ℹ️ Rider {rider.id} was already in assignment group for order {order.order_number}")
                
        except Order.DoesNotExist:
            print(f"❌ Order {order_number} not found")
        except Exception as e:
            print(f"❌ Error processing order {order_number}: {str(e)}")
            
    print("\n✅ Assignment complete! Check the rider dashboard to see if orders appear now.")
else:
    print("❌ Cannot fix orders: No riders available in the system.")
