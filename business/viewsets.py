from rest_framework import viewsets, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
import logging
import sys
from django.db.models import Q

from .models import Business, Category, Product
from .serializers import CategorySerializer, BusinessSerializer, ProductSerializer

# Set up logging
logger = logging.getLogger('business.viewsets')

# Clear any existing handlers to avoid duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

# Add a debug log to confirm logger is working
logger.debug("Business viewsets logger initialized")

class BusinessCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving categories for the current user's business.
    """
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]  # Changed from IsAuthenticated to AllowAny for testing
    
    def list(self, request, *args, **kwargs):
        """Override list method to add extra logging"""
        # Find business first
        user = request.user
        if user.is_authenticated:
            try:
                business = Business.objects.get(user=user)
                print(f"\n\nFound business: {business.name} (ID: {business.id}) for user {user.username}")

                # Count categories up front
                categories = Category.objects.filter(business=business)
                print(f"Found {categories.count()} categories for business {business.name}")
                
                # Print each category
                if categories.exists():
                    print("Categories found:")
                    for idx, cat in enumerate(categories):
                        print(f"  {idx+1}. {cat.name} (ID: {cat.id})")
                else:
                    print("NO CATEGORIES FOUND FOR THIS BUSINESS!")
            except Exception as e:
                print(f"Error getting business: {e}")

        print("\n" + "*" * 50)
        print("CATEGORIES API CALLED!!!! - Breaking through any buffering")
        print("*" * 50)
        print(f"\n[CATEGORIES API] REQUEST RECEIVED at {request.path}")
        
        # Call the parent class's list method to handle the actual response
        return super().list(request, *args, **kwargs)


class BusinessViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows businesses to be viewed or edited.
    """
    serializer_class = BusinessSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """
        Get and filter businesses.
        """
        queryset = Business.objects.filter(is_active=True)
        
        # Print all available businesses to console
        all_businesses = list(queryset.values('id', 'name', 'owner_name', 'location', 'region'))
        
        print("\n" + "="*100)
        print("BUSINESSES IN DATABASE:")
        print("-"*100)
        for idx, biz in enumerate(all_businesses, 1):
            print(f"{idx}. {biz['name']} (ID: {biz['id']})")
            print(f"   Owner: {biz['owner_name']}")
            print(f"   Location: {biz['location']}")
            print(f"   Region: {biz['region']}")
            print("-"*100)
        print(f"Total active businesses: {len(all_businesses)}")
        print("="*100 + "\n")
        
        # Apply filters
        search = self.request.query_params.get('search')
        region = self.request.query_params.get('region')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(owner_name__icontains=search) |
                Q(location__icontains=search)
            )
        
        if region:
            queryset = queryset.filter(region=region)
        
        return queryset.order_by('name')
    
    def list(self, request, *args, **kwargs):
        # Ensure we're logging to console
        import sys
        
        # Get the queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        # Log the request
        print(f"\nAPI Request: {request.method} {request.path}")
        print(f"Query Params: {dict(request.query_params)}")
        print(f"Found {queryset.count()} businesses")
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows products to be viewed or edited.
    """
    # Start with all products for debugging
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    
    def list(self, request, *args, **kwargs):
        """
        Return a clean list of products for the specified business.
        Format matches Flutter app's expected response.
        """
        import logging
        import sys
        
        # Configure root logger to output to console
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Create console handler if it doesn't exist
        if not root_logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        logger = logging.getLogger('business')
        
        try:
            print("\n" + "="*80)
            print("PRODUCT LIST REQUEST RECEIVED")
            print("="*80)
            print(f"URL: {request.get_full_path()}")
            print(f"Query Params: {dict(request.query_params)}")
            
            # Log request headers
            print("\nREQUEST HEADERS:")
            for header, value in request.META.items():
                if header.startswith('HTTP_'):
                    print(f"{header[5:].replace('_', '-').title()}: {value}")
            
            # Get the queryset
            queryset = self.filter_queryset(self.get_queryset())
            print(f"\nFound {queryset.count()} products in database")
            
            # Log some sample products if they exist
            if queryset.exists():
                print("\nSAMPLE PRODUCTS:")
                for i, product in enumerate(queryset[:3]):  # Show first 3 products
                    print(f"{i+1}. {product.name} (ID: {product.id}, Available: {product.is_available})")
            
            # Serialize the data
            serializer = self.get_serializer(queryset, many=True)
            
            # Create response data in the format expected by Flutter app
            response_data = {
                'status': 'success',
                'count': queryset.count(),
                'results': serializer.data  # Flutter is looking for 'results' key
            }
            
            # Log the response (for debugging)
            import json
            print("\n" + "="*80)
            print("SENDING RESPONSE TO FLUTTER APP:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            print("="*80 + "\n")
            
            return Response(response_data)
            
        except Exception as e:
            error_msg = f"Error fetching products: {str(e)}"
            print(f"\nERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            
            error_response = {
                'success': False,
                'message': error_msg,
                'data': []
            }
            
            print("\nSENDING ERROR RESPONSE:")
            print(json.dumps(error_response, indent=2))
            return Response(error_response, status=status.HTTP_200_OK)
    
    def get_queryset(self):
        """
        Get the list of products filtered by business_id and other optional filters.
        Returns all products regardless of availability.
        """
        queryset = Product.objects.all()
        
        # Get query parameters
        params = self.request.query_params
        business_id = params.get('business_id')
        
        # Filter by business_id if provided
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        
        # Apply optional filters
        category_id = params.get('category_id')
        search = params.get('search')
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.select_related('business', 'category').order_by('name')


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows categories to be viewed or edited.
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """
        Get categories - returns all general categories plus any custom categories
        for the specified business, with business-specific categories taking precedence
        over general ones with the same name.
        """
        from django.db.models import Q, Case, When, Value, BooleanField
        
        # Get business_id from query params if provided
        business_id = self.request.query_params.get('business_id')
        
        # Start with all active categories
        queryset = Category.objects.filter(is_active=True)
        
        # If business_id is provided, get both general and business-specific categories
        if business_id:
            try:
                business = Business.objects.get(id=business_id)
                print(f"\n[CATEGORIES API] Found business: {business.name} (ID: {business.id})")
                
                # Get all general categories (no business) and categories for this business
                queryset = queryset.filter(Q(business_id=business_id) | Q(business__isnull=True))
                
                # Add a field to prioritize business-specific categories in sorting
                queryset = queryset.annotate(
                    is_business_specific=Case(
                        When(business_id=business_id, then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField()
                    )
                )
                
                # Order by business-specific first, then by name
                queryset = queryset.order_by('-is_business_specific', 'name')
                
            except Business.DoesNotExist:
                print(f"\n[CATEGORIES API] Business with ID {business_id} not found")
                # If business not found, return only general categories
                queryset = queryset.filter(business__isnull=True)
        else:
            # If no business_id, only get general categories
            queryset = queryset.filter(business__isnull=True)
        
        # Apply additional filters if provided
        category_type = self.request.query_params.get('type')
        if category_type:
            print(f"[CATEGORIES API] Filtering by type: {category_type}")
            queryset = queryset.filter(category_type=category_type)
        
        # Debug output
        print("\n" + "*" * 80)
        print("CATEGORIES DEBUG")
        print("*" * 80)
        print(f"Business ID from params: {business_id}")
        print(f"Found {queryset.count()} categories")
        
        # Print categories with their business info (limit to 10 for brevity)
        for idx, cat in enumerate(queryset[:10], 1):
            business_info = f"Business: {cat.business.name} (ID: {cat.business_id})" if cat.business else "General (No Business)"
            print(f"{idx}. {cat.name} (ID: {cat.id}, {business_info})")
        if queryset.count() > 10:
            print(f"... and {queryset.count() - 10} more categories")
        print("*" * 80 + "\n")
        
        return queryset

    def list(self, request, *args, **kwargs):
        """
        List categories with detailed debugging information.
        """
        print("\n" + "="*80)
        print("CATEGORIES API REQUEST")
        print("="*80)
        print(f"Method: {request.method}")
        print(f"URL: {request.build_absolute_uri()}")
        print(f"User: {request.user}")
        print(f"Query Params: {request.GET}")
        
        try:
            # Get the response from the parent class
            response = super().list(request, *args, **kwargs)
            
            # Safely log response data
            print("\n[CATEGORIES API] Response:")
            print(f"Status: {response.status_code}")
            
            # Handle different response data formats
            if hasattr(response, 'data'):
                if isinstance(response.data, list):
                    print(f"Items count: {len(response.data)}")
                    if response.data:
                        print(f"First item: {response.data[0]}")
                elif isinstance(response.data, dict):
                    if 'results' in response.data:  # Paginated response
                        print(f"Items count: {len(response.data.get('results', []))}")
                        if response.data.get('results'):
                            print(f"First item: {response.data['results'][0]}")
                    else:
                        print(f"Response data: {response.data}")
            
            # Ensure output is flushed
            import sys
            sys.stdout.flush()
            
            return response
            
        except Exception as e:
            print(f"\n[CATEGORIES API] ERROR: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
        if business_id:
            print(f"[CATEGORIES API] Filtering by business_id: {business_id}")
            try:
                # Filter categories by the specified business_id
                business = Business.objects.get(id=business_id)
                print(f"Found business by ID: {business.name} (ID: {business.id})")
                categories = Category.objects.filter(business=business).order_by('name')
                print(f">> FOUND {categories.count()} CATEGORIES FOR BUSINESS ID: {business_id} <<")
                return categories
            except Business.DoesNotExist:
                print(f"[CATEGORIES API] Business with ID {business_id} not found")
                return Category.objects.none()
            except Exception as e:
                print(f"[CATEGORIES API] Error filtering by business_id: {str(e)}")
                return Category.objects.none()
        
        # Handle anonymous users for testing (when no business_id provided)
        if not user.is_authenticated:
            print(f"[CATEGORIES API] Anonymous user - returning all categories for testing")
            return Category.objects.all().order_by('name')

        # For authenticated users, get their business and filter categories
        try:
            print(f"\nGetting categories for authenticated user: {user.username}")
            business = Business.objects.get(user=user)
            print(f"Found business: {business.name} (ID: {business.id})")
            
            # Now filter by business
            categories = Category.objects.filter(business=business).order_by('name')
            print(f">> FOUND {categories.count()} CATEGORIES FOR BUSINESS: {business.name} <<")
            
            # Debug output of ALL categories
            if categories.exists():
                print("CATEGORIES FOUND:")
                for idx, cat in enumerate(categories):
                    print(f"  {idx+1}. ID={cat.id}, Name={cat.name}, Business={cat.business.name if cat.business else 'None'}")
            else:
                print(f">> NO CATEGORIES FOUND FOR BUSINESS: {business.name} <<")
                
            # Return the filtered queryset
            return categories
        except Business.DoesNotExist:
            print(f"[CATEGORIES API] ERROR: No business found for user: {user.username}")
            logger.error(f"No business found for user: {user.username}")
            return Category.objects.none()
        except Exception as e:
            logger.error(f"Error retrieving categories: {str(e)}")
            print(f"[CATEGORIES API] ERROR: {str(e)}")
            print(f"[CATEGORIES API] ERROR DETAILS: {type(e).__name__}")
            import traceback
            print(f"[CATEGORIES API] TRACEBACK: {traceback.format_exc()[:500]}")
            return Category.objects.none()  # Return empty queryset on error
