from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .viewsets import BusinessCategoryViewSet, BusinessViewSet, ProductViewSet, CategoryViewSet
from . import public_api
from .api_views import ProductListView, BusinessListView

# Set up DRF router
router = DefaultRouter()
router.register(r'businesses', BusinessViewSet, basename='business')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')

# Debug print to see what URLs are being registered
for url in router.urls:
    print(f"[DEBUG] Router URL: {url.pattern}")

from django.contrib.auth.views import LogoutView

app_name = 'business'

urlpatterns = [
    # Public API endpoints (no authentication required)
    path('public-api/categories/create/', public_api.create_category, name='public_create_category'),
    
    # Include DRF router URLs
    path('', include(router.urls)),
    
    # Standard view URLs
    path('list/', views.business_list, name='business_list'),
    path('api/data/', views.get_businesses_data, name='get_businesses_data'),
    path('register/', views.business_register, name='business_register'),  # Business Registration URL
    path('login/', views.business_login, name='business_login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('logout/', LogoutView.as_view(next_page='business:business_login'), name='logout'),
    path('sales-history/', views.sales_history, name='sales_history'),
    path('sales-history/export/', views.export_sales_history_excel, name='export_sales_history'),
    path('sales-history/import/', views.import_sales_history_excel, name='import_sales_history'),
    path('earnings/', views.earnings, name='earnings'),
    path('profile/', views.business_profile, name='profile'),
    path('dashboard/', views.business_dashboard, name='business_dashboard'),
    path('add_product/', views.add_product, name='add_product'),
    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/public-add/', views.public_add_category, name='public_add_category'),
    path('create-business/', views.create_business, name='create_business'),
    path('mark-order-ready/', views.mark_order_ready, name='mark_order_ready'),
    path('verify-otp/<int:user_id>/', views.verify_otp, name='verify_otp'),  # OTP verification
    path('resend-otp/', views.resend_otp, name='resend_otp'),  # Resend OTP
    
    # API v1 endpoints
    path('api/v1/', include([
        # Business endpoints
        path('businesses/', BusinessListView.as_view(), name='business_list'),
        path('products/', ProductListView.as_view(), name='product_list'),
        
        # Include router URLs
        path('', include(router.urls)),
    ])),
    
    # Legacy API endpoint - now handled by the router
    # path('api/categories/', apis.business_categories, name='business_categories'),
]
