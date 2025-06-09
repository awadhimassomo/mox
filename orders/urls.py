from django.urls import path
from . import views
from .views import CreateOrderAPIView

app_name = 'orders'

urlpatterns = [
    # API Endpoints (v1)
    path('api/orders/create/', CreateOrderAPIView.as_view(), name='api_order_create'),
    path('create/', CreateOrderAPIView.as_view(), name='order_create'),  # Alias for backward compatibility
    path('api/complete-order/<int:order_id>/', views.complete_order_api, name='complete_order_api'),
    
    # Web Views
    path("incoming-orders/", views.incoming_orders, name="incoming_orders"),
    path("orders/", views.orders, name="orders"),
    path("order-list/", views.orders, name="order_list"),  # Alias for customer-facing orders view
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
]
