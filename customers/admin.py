from django.contrib import admin
from .models import CustomerProfile, DeliveryAddress, Cart, CartItem, Favorite


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number')
    list_filter = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'default_address')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('favorite_businesses',)


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer', 'street', 'area', 'city', 'is_default')
    list_filter = ('city', 'is_default')
    search_fields = ('name', 'street', 'area', 'city', 'landmark', 'customer__phone_number')
    raw_id_fields = ('customer',)
    list_editable = ('is_default',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'business', 'total_items', 'subtotal', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('customer__phone_number', 'customer__user__first_name', 'customer__user__last_name', 'business__name')
    raw_id_fields = ('customer', 'business')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'unit_price', 'total_price')
    list_filter = ('cart__created_at',)
    search_fields = ('cart__customer__phone_number', 'product__name')
    raw_id_fields = ('cart', 'product')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'business', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('customer__phone_number', 'customer__user__first_name', 'customer__user__last_name', 'business__name')
    readonly_fields = ('created_at',)
    raw_id_fields = ('customer', 'business')
