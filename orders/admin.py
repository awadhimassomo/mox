from django.contrib import admin
from .models import Order, OrderAssignmentGroup, OrderRiderAction, TransportMode

# Register your models here.

class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'customer_name')
    readonly_fields = ('order_number', 'uuid_tracking')
    

class OrderAssignmentGroupAdmin(admin.ModelAdmin):
    list_display = ('order', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('order__order_number',)
    
    
class OrderRiderActionAdmin(admin.ModelAdmin):
    list_display = ('order', 'rider', 'action_type', 'timestamp', 'location_lat', 'location_lng')
    list_filter = ('action_type', 'timestamp')
    search_fields = ('order__order_number', 'rider__user__first_name', 'rider__user__last_name', 'notes')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('order', 'rider', 'rider__user')


class TransportModeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'price_per_km', 'max_distance', 'max_weight', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


admin.site.register(Order, OrderAdmin)
admin.site.register(OrderAssignmentGroup, OrderAssignmentGroupAdmin)
admin.site.register(OrderRiderAction, OrderRiderActionAdmin)
admin.site.register(TransportMode, TransportModeAdmin)
