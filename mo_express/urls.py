
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers


# Create a router and register our viewsets with it
router = routers.DefaultRouter()


urlpatterns = [
    path('', include('website.urls')),  # Make website the root URL
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('operations/', include('operations.urls')),
    path('customers/', include('customers.urls')),
    path('riders/', include('riders.urls')),
    path('business/', include('business.urls')),
    path("orders/", include("orders.urls")),
    path('user-verification/', include('user_verification.urls')),
    path("__reload__/", include("django_browser_reload.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
