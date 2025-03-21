from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'riders', views.RiderViewSet)
app_name = 'riders'

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.rider_login, name='login'),
    path('logout/', views.rider_logout, name='logout'),
    path('rider-logout/', views.rider_logout, name='rider_logout'),
    path('register/', views.rider_register, name='rider_register'),
    path('dashboard/', views.rider_dashboard, name='dashboard'),
    path('operations/', include('operations.urls')),
    path('earning/', views.rider_earnings_view, name='rider_earnings'),
    path('history/', views.rider_history_view, name='rider_history'),
    path('profile/', views.rider_profile_view, name='rider_profile'),
    path('far-orders/', views.far_orders_view, name='far_orders'),
    path("update-location/", views.update_rider_location, name="update_rider_location"),
    path('order/<int:order_id>/accept/', views.accept_order, name='accept_order'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('order/<int:order_id>/in-transit/', views.mark_order_in_transit, name='mark_order_in_transit'),
    path('order/<int:order_id>/delivered/', views.mark_order_delivered, name='mark_order_delivered'),
    path('api/get-kijiwe-locations/', views.get_kijiwe_locations, name='get_kijiwe_locations'),  # URL for kijiwe locations
    
    # API endpoints
    path('api/update-location/', views.UpdateRiderLocation.as_view(), name='update_location'),
    path('api/resend-otp/', views.ResendOTPView.as_view(), name='api_resend_otp'),
    path('api/incoming-orders/', views.incoming_orders_api, name='get_incoming_orders'),
    path('api/accept-order/<int:order_id>/', views.accept_order_api, name='accept_order_api'),
    path('api/decline-order/<int:order_id>/', views.decline_order_api, name='decline_order_api'),
    path('api/start-delivery/<int:order_id>/', views.start_delivery_api, name='start_delivery_api'),
    path('api/complete-order/<int:order_id>/', views.complete_order_api, name='complete_order_api'),
    path('api/record-penalty/<int:order_id>/', views.record_penalty_api, name='record_penalty_api'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('api/debug-coordinates/', views.debug_coordinates, name='debug_coordinates'),
    path('api/rider/earnings-stats/', views.rider_earnings_stats_api, name='rider_earnings_stats_api'),
    path('api/rider/earnings-chart/', views.rider_earnings_chart_api, name='rider_earnings_chart_api'),
    path('api/rider/update-profile/', views.update_rider_profile, name='update_rider_profile'),
    path('api/manually-assign-orders/', views.manually_assign_orders, name='manually_assign_orders'),
]
