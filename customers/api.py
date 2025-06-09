"""
API URL Configuration for customers app.
This module is loaded lazily to avoid AppRegistryNotReady errors.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Define a function to lazily load URL patterns when needed
def get_api_urlpatterns():
    from rest_framework.routers import DefaultRouter
    from .views import CustomerLoginAPIView, CustomerProfileViewSet, UserViewSet
    from . import views
    
    # Create a router for API viewsets
    router = DefaultRouter()
    router.register(r'profiles', CustomerProfileViewSet, basename='customerprofile')
    router.register(r'users', UserViewSet, basename='user')
    
    # API URL patterns
    patterns = [
        # Authentication endpoints
        path('auth/login/', CustomerLoginAPIView.as_view(), name='api-login'),
        path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        
        # Profile endpoints
        path('api/', include(router.urls)),
        
        # Other API endpoints
        path('nearby-businesses/', views.nearby_businesses_api, name='nearby_businesses_api'),
        path('calculate-delivery-fee/', views.calculate_delivery_fee, name='calculate_delivery_fee_api'),
    ]
    
    return patterns

# Django's URL resolver looks for this variable - we define it as a function call
# that will only execute when Django is ready to import views
urlpatterns = get_api_urlpatterns()
