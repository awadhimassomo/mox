from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Home and Business Views
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('search/', views.search, name='search'),
    path('business/<int:business_id>/', views.business_detail, name='business_detail'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('api/nearby-businesses/', views.nearby_businesses_api, name='nearby_businesses_api'),
    path('api/calculate-delivery-fee/', views.calculate_delivery_fee, name='calculate_delivery_fee_api'),
    
    # Cart Management
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('update_cart/<int:item_id>/', views.update_cart_item_ajax, name='update_cart_item_ajax'),
    
    # Checkout Process
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/<int:business_id>/', views.checkout, name='checkout_with_business'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('calculate-delivery-fe/', views.calculate_delivery_fee, name='calculate_delivery_fee'),
    
    # Featured Business Checkout
    path('business/<int:business_id>/featured-checkout/', views.featured_business_checkout, name='featured_business_checkout'),
    path('place-featured-order/', views.place_featured_order, name='place_featured_order'),
    
    # Order Management
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('calculate-delivery-fee/', views.calculate_delivery_fee_view, name='calculate_delivery_fee'),
    
    # Profile and Address Management
    path('profile/', views.profile, name='profile'),
    path('addresses/', views.manage_addresses, name='manage_addresses'),
    path('addresses/add/', views.add_address, name='add_address'),
    path('addresses/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('addresses/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('addresses/add-from-coordinates/', views.add_address_from_coordinates, name='add_address_from_coordinates'),
    path('addresses/set-default/', views.set_default_address, name='set_default_address'),
    
    # Favorites
    path('business/toggle-favorite/', views.toggle_favorite_business, name='toggle_favorite_business'),
]
