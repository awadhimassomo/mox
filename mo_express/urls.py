
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Import views
from business.views import BusinessViewSet, ProductViewSet, BusinessRegistrationAPIView, CategoryViewSet
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
# Don't import views here - we'll use django's path() resolution mechanism

# Add an explicit login URL pattern to the main URL configuration
# This avoids the need for lazy loading this particular view
# Other customer views will be loaded from customers.urls

# Initialize the main router
router = routers.DefaultRouter()
router.register(r'businesses', BusinessViewSet, basename='business')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')

# API v1 URL patterns
v1_patterns = [
    # Include business app API URLs
    path('business/', include('business.urls')),
    
    # Category endpoints
    path('categories/', include([
        path('', CategoryViewSet.as_view({'get': 'list', 'post': 'create'}), name='category-list'),
        path('<int:pk>/', CategoryViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }), name='category-detail'),
    ])),
    
    # Customer web endpoints
    path('customers/', include(('customers.urls', 'customers'))),
    
    # Customer API endpoints - imported by name as a string to avoid early imports
    path('customers/', include('customers.api')),
    
    # Authentication
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
]

# API URL patterns
api_patterns = [
    path('v1/', include(v1_patterns)),
]

# Schema View for Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Mo-Express API",
        default_version='v1',
        description="API documentation for Mo-Express",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@moexpress.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[
        path('api/', include(api_patterns)),
    ],  # Explicitly set the URL patterns for the schema
)

# Main URL patterns
urlpatterns = [
    # Website URLs
    path('', include('website.urls')),  # Make website the root URL
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include(api_patterns)),
    
    # Other apps
    path('operations/', include('operations.urls')),
    path('riders/', include('riders.urls')),
    path('business/', include('business.urls')),
    path("orders/", include("orders.urls")),
    path('user-verification/', include('user_verification.urls')),
    path("__reload__/", include("django_browser_reload.urls")),
]

# Add API documentation URLs
urlpatterns += [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Also serve from STATICFILES_DIRS for development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
