from django.contrib import admin
from .models import ServiceType, ServiceBooking, RiderServicePreference

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'base_price', 'price_per_km', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)

@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ('booking_number', 'customer', 'service_type', 'status', 'scheduled_date', 'total_price')
    list_filter = ('status', 'service_type', 'scheduled_date')
    search_fields = ('booking_number', 'customer__username', 'pickup_address', 'destination_address')
    readonly_fields = ('booking_number', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'scheduled_date'
    ordering = ('-scheduled_date',)

@admin.register(RiderServicePreference)
class RiderServicePreferenceAdmin(admin.ModelAdmin):
    list_display = ('rider', 'is_available', 'working_hours_start', 'working_hours_end', 'service_radius_km')
    list_filter = ('is_available', 'services')
    search_fields = ('rider__username', 'rider__email')
    filter_horizontal = ('services',)
