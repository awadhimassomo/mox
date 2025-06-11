from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'service-types', views.ServiceTypeViewSet)
router.register(r'rider-preferences', views.RiderServicePreferenceViewSet, basename='riderpreference')
router.register(r'bookings', views.ServiceBookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
    path('services/available/', views.AvailableServicesView.as_view(), name='available-services'),
    path('services/<int:service_type_id>/available-riders/', views.AvailableRidersView.as_view(), name='available-riders'),
]
