from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path("incoming-orders/", views.incoming_orders, name="incoming_orders"),
    path("orders/", views.orders, name="orders"),
    path("order-list/", views.orders, name="order_list"),  # Alias for customer-facing orders view
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path('api/complete-order/<int:order_id>/', views.complete_order_api, name='complete_order_api'),
]
