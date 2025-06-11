from rest_framework import viewsets, status, permissions, mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone

from operations.models import CustomUser
from .models import ServiceType, ServiceBooking, RiderServicePreference
from .serializers import (
    ServiceTypeSerializer, ServiceBookingSerializer,
    RiderServicePreferenceSerializer, ServiceBookingStatusUpdateSerializer
)

# Custom permissions
class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit objects.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to admin users.
        return request.user and request.user.is_staff

class IsRider(permissions.BasePermission):
    """
    Custom permission to only allow riders to access the view.
    """
    def has_permission(self, request, view):
        return hasattr(request.user, 'rider')

class IsCustomer(permissions.BasePermission):
    """
    Custom permission to only allow customers to access the view.
    """
    def has_permission(self, request, view):
        return not hasattr(request.user, 'rider') and not request.user.is_staff

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow admins to do anything
        if request.user and request.user.is_staff:
            return True
            
        # Check if the user is the owner of the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'customer'):
            return obj.customer == request.user
        elif hasattr(obj, 'rider') and obj.rider:
            return obj.rider.user == request.user
            
        return False

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ServiceTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing service types.
    """
    queryset = ServiceType.objects.filter(is_active=True)
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'base_price', 'created_at']
    pagination_class = StandardResultsSetPagination

class RiderServicePreferenceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing rider service preferences.
    """
    serializer_class = RiderServicePreferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsRider]
    
    def get_queryset(self):
        # Riders can only see their own preferences
        if self.request.user.is_authenticated and hasattr(self.request.user, 'rider'):
            return RiderServicePreference.objects.filter(rider=self.request.user.rider)
        return RiderServicePreference.objects.none()
    
    def perform_create(self, serializer):
        # Automatically set the rider to the current user's rider profile
        if hasattr(self.request.user, 'rider'):
            serializer.save(rider=self.request.user.rider)
        else:
            raise serializers.ValidationError("User is not a rider.")

class ServiceBookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing service bookings.
    """
    serializer_class = ServiceBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'service_type', 'rider']
    search_fields = ['booking_number', 'pickup_address', 'destination_address']
    ordering_fields = ['scheduled_date', 'created_at', 'total_price']
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = ServiceBooking.objects.all()
        
        # Admins can see all bookings
        if user.is_staff:
            return queryset
            
        # Riders can see their assigned bookings
        if hasattr(user, 'rider'):
            return queryset.filter(rider=user.rider)
            
        # Customers can only see their own bookings
        return queryset.filter(customer=user)
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        elif self.action in ['update_status']:
            permission_classes = [permissions.IsAuthenticated, IsRider]
        else:
            permission_classes = [permissions.IsAuthenticated]
            
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        # Set the customer to the current user
        serializer.save(customer=self.request.user)
        
    def get_serializer_context(self):
        """
        Add the request to the serializer context.
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Custom action to update booking status.
        """
        booking = self.get_object()
        serializer = ServiceBookingStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Only allow riders to update status of their own bookings
            if hasattr(request.user, 'rider') and booking.rider != request.user.rider:
                return Response(
                    {"detail": "You can only update status of your own bookings."},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            serializer.update(booking, serializer.validated_data)
            return Response(ServiceBookingSerializer(booking).data)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AvailableServicesView(APIView):
    """
    API endpoint to list all available services.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, format=None):
        services = ServiceType.objects.filter(is_active=True)
        serializer = ServiceTypeSerializer(services, many=True)
        return Response(serializer.data)

class AvailableRidersView(APIView):
    """
    API endpoint to list available riders for a specific service.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, service_type_id, format=None):
        try:
            service_type = ServiceType.objects.get(id=service_type_id, is_active=True)
            
            # Get users who are riders, available, and provide this service type
            available_riders = CustomUser.objects.filter(
                is_active=True,
                rider__is_available=True,
                rider__service_type=service_type.code
            ).select_related('rider')
            
            # You can add more filtering here based on location, etc.
            serializer = RiderSerializer(available_riders, many=True, context={'request': request})
            
            return Response({
                'service': ServiceTypeSerializer(service_type).data,
                'available_riders': serializer.data,
                'count': len(serializer.data)
            })
            
        except ServiceType.DoesNotExist:
            return Response(
                {"detail": "Service type not found or inactive."},
                status=status.HTTP_404_NOT_FOUND
            )
