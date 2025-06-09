from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from .models import Product, Category, Business
from .serializers import ProductSerializer, CategorySerializer, BusinessSerializer
import logging
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger(__name__)

class ProductListView(generics.ListAPIView):
    """
    API endpoint that allows products to be viewed.
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]  # Allow any user to view products

    def get_queryset(self):
        """
        Optionally filter products by category, business, or search term.
        """
        queryset = Product.objects.filter(is_available=True).select_related('category', 'business')
        
        # Filter by category ID
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # Filter by business ID
        business_id = self.request.query_params.get('business_id')
        if business_id:
            queryset = queryset.filter(business_id=business_id)
            
        # Search by product name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
            
        return queryset.order_by('name')

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'status': 'success',
                'count': len(serializer.data),
                'data': serializer.data
            })
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}", exc_info=True)
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BusinessListView(generics.ListAPIView):
    """
    API endpoint that allows businesses to be viewed.
    """
    queryset = Business.objects.filter(is_active=True).select_related('user')
    serializer_class = BusinessSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['region', 'is_featured']
    search_fields = ['name', 'owner_name', 'location']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # Pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'status': 'success',
                    'count': self.paginator.page.paginator.count,
                    'next': self.paginator.get_next_link(),
                    'previous': self.paginator.get_previous_link(),
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'status': 'success',
                'count': len(serializer.data),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error fetching businesses: {str(e)}", exc_info=True)
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
