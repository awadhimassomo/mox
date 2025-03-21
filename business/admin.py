from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Business, Product

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_quantity', 'business', 'is_available', 'display_unit')
    list_filter = ('category', 'business', 'is_available')
    search_fields = ('name', 'category', 'business__name')
    ordering = ('category', 'name')

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'category', 'business', 'image', 'is_available')
        }),
        (_('Pricing & Stock'), {
            'fields': ('price', 'stock_quantity', 'unit')
        }),
        (_('Gas Details'), {
            'fields': ('gas_type', 'tank_size'),
            'classes': ('collapse',),
        }),
        (_('Food Details'), {
            'fields': ('preparation_time', 'is_vegan', 'is_halal'),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'display_unit')

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('business')

    def get_fieldsets(self, request, obj=None):
        """Dynamically adjust fieldsets based on category"""
        fieldsets = list(super().get_fieldsets(request, obj))
        
        if obj:
            if obj.category != 'gas':
                fieldsets = [fs for fs in fieldsets if fs[0] != _('Gas Details')]
            if obj.category != 'food':
                fieldsets = [fs for fs in fieldsets if fs[0] != _('Food Details')]
        return fieldsets
    
    
    
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'region', 'created_at')  # Fields to show in list view
    list_filter = ('region', 'created_at')  # Filters on sidebar
    search_fields = ('name', 'phone', 'user__phone')  # Search by name, phone, or user phone
    ordering = ('-created_at',)  # Order by newest businesses first


admin.site.register(Business, BusinessAdmin)
admin.site.register(Product, ProductAdmin)
