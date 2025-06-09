from rest_framework import serializers
from .models import Order, OrderItem, TransportMode
from business.models import Product, Business  # Added Business import
from customers.models import CustomerProfile, DeliveryAddress

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    pieces = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0.01,
        error_messages={
            'invalid': 'Please enter a valid number for pieces.',
            'min_value': 'Pieces must be greater than 0.'
        }
    )
    
    class Meta:
        model = OrderItem
        fields = ['product_id', 'quantity', 'unit_price', 'pieces', 'notes']
        extra_kwargs = {
            'unit_price': {
                'required': True,
                'min_value': 0.01,
                'error_messages': {
                    'invalid': 'Please enter a valid price.',
                    'min_value': 'Price must be greater than 0.'
                }
            },
            'quantity': {
                'min_value': 1,
                'error_messages': {
                    'min_value': 'Quantity must be at least 1.'
                }
            },
            'notes': {'required': False, 'allow_blank': True},
        }
    
    def validate(self, data):
        # Ensure pieces is a valid decimal if provided
        pieces = data.get('pieces')
        if pieces is not None:
            try:
                pieces = float(pieces)
                if pieces <= 0:
                    raise serializers.ValidationError({
                        'pieces': 'Pieces must be greater than 0.'
                    })
                data['pieces'] = pieces
            except (TypeError, ValueError):
                raise serializers.ValidationError({
                    'pieces': 'Please enter a valid number for pieces.'
                })
        return data

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomerProfile.objects.all(),
        source='customer',
        required=False,
        allow_null=True
    )
    business_id = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.all(),
        source='business',
        required=True
    )
    delivery_address_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryAddress.objects.all(),
        source='delivery_address',
        required=False,
        allow_null=True
    )
    transport_mode_id = serializers.PrimaryKeyRelatedField(
        queryset=TransportMode.objects.filter(is_active=True),
        source='transport_mode',
        required=True
    )
    
    class Meta:
        model = Order
        fields = [
            'customer_id', 'business_id', 'delivery_address_id', 'transport_mode_id',
            'delivery_location', 'delivery_latitude', 'delivery_longitude',
            'payment_method', 'notes', 'items'
        ]
        extra_kwargs = {
            'delivery_location': {'required': True},
            'delivery_latitude': {'required': True},
            'delivery_longitude': {'required': True},
            'payment_method': {'required': True},
        }
    
    def validate(self, data):
        # Add any custom validation here
        if 'delivery_latitude' not in data or 'delivery_longitude' not in data:
            raise serializers.ValidationError("Delivery coordinates are required")
        
        if not data.get('items'):
            raise serializers.ValidationError("At least one order item is required")
            
        return data
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        # Calculate and update order total
        order.calculate_totals()
        
        return order
