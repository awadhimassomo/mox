from django.urls import path
from . import views
from .otp_views import SendOTPView, ResendOTPView, VerifyOTPView

app_name = 'operations'

urlpatterns = [
    # Web views
    path('orders/', views.order_list, name='order_list'),
    path('kijiwe/', views.kijiwe_list, name='kijiwe_list'),
    path('kijiwe/create/', views.kijiwe_create, name='kijiwe_create'),
    path('kijiwe/<int:pk>/', views.kijiwe_detail, name='kijiwe_detail'),
    path('kijiwe-by-region/', views.kijiwe_by_region_api, name='kijiwe_by_region'),
    path('logout/', views.logout_view, name='logout'), 
    path('register/', views.dashboard_register, name='dashboard_register'),
    path('login/', views.OperationsLoginView.as_view(), name='login'),
    path('loginapi/', views.dashboard_login, name='loginapi'),
    path('dashboard/', views.dashboard, name='dashboard'), # Add logout URL
    path('orders/history/', views.order_history_api, name='order_history'),
    path('riders/', views.riders_list, name='riders_list'),
    path('businesses/', views.business_list, name='business_list'),
    # API endpoints
    path('api/orders/', views.order_list_api, name='order_list_api'),
    path('api/kijiwe/', views.kijiwe_list_api, name='kijiwe_list_api'),
    path('api/kijiwe/<int:pk>/', views.kijiwe_detail_api, name='kijiwe_detail_api'),
    
    # OTP endpoints
    path('api/otp/send/', SendOTPView.as_view(), name='send_otp'),
    path('api/otp/resend/', ResendOTPView, name='resend_otp'),
    path('api/otp/verify/', VerifyOTPView.as_view(), name='verify_otp'),
    path('api/riders/', views.riders_api, name='riders_api'),
    
    # Rider stat endpoint
    path('api/rider/stats/<int:rider_id>/', views.rider_stats_api, name='rider_stats_api'),

    # Find nearby riders using UUID
    path('api/orders/<int:order_id>/nearby-riders/', views.nearby_riders, name='nearby_riders'),

    # Assign rider using UUID
    path('api/orders/uuid/<uuid:order_uuid>/assign/<int:rider_id>/', views.assign_rider, name='assign_rider'),
    
    # Assign multiple riders using UUID
    path('api/orders/uuid/<uuid:order_uuid>/assign-multiple/', views.assign_multiple_riders, name='assign_multiple_riders'),
    
    

    path('api/dashboard-data/', views.dashboard_data, name='dashboard_data'),
    path('api/orders/<int:order_id>/assign/<int:rider_id>/', views.assign_rider, name='assign_rider'),
    path('api/orders/<int:order_id>/assign-multiple/', views.assign_multiple_riders, name='assign_multiple_riders'),
    path('api/orders/<int:order_id>/', views.order_details, name='order_details'),

]
