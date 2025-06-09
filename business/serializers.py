from rest_framework import serializers
from .models import Business, Product, Category

class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            'id', 'name', 'owner_name', 'address', 'phone',
            'location', 'latitude', 'longitude', 'region',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    business_name = serializers.CharField(source='business.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'description', 
            'category', 
            'category_name',
            'unit',
            'price',
            'stock_quantity',
            'is_available',
            'business',
            'business_name',
            'image',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Add full URL for image if it exists
        if 'image' in representation and representation['image']:
            request = self.context.get('request')
            if request is not None:
                representation['image'] = request.build_absolute_uri(representation['image'])
        
        # Add human-readable display for unit
        if 'unit' in representation:
            representation['unit_display'] = dict(Product.UNIT_CHOICES).get(representation['unit'], representation['unit'])
        # Add tank size display if applicable
        if instance.tank_size is not None:
            tank_size_display = dict(Product._meta.get_field('tank_size').flatchoices).get(instance.tank_size, str(instance.tank_size))
            representation['tank_size_display'] = tank_size_display
        
        return representation

class CategorySerializer(serializers.ModelSerializer):
    # Ensure parent is correctly handled - it can be null
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), 
        allow_null=True, 
        required=False
    )
    
    # Add a 'type' field that maps to category_type for frontend compatibility
    type = serializers.CharField(source='category_type', read_only=True)
    
    # Get parent ID separately for frontend compatibility
    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent',
        queryset=Category.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'is_active', 
            'parent', 'parent_id', 'category_type', 'type', 'is_top_level', 'full_name', 'has_children'
        ]
        read_only_fields = ['slug', 'full_name', 'has_children']
