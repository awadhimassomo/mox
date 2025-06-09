from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Category, Business
from django.utils.text import slugify
import random
import string
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view, schema

@csrf_exempt
@api_view(['POST'])
@swagger_auto_schema(
    operation_summary="Create a new category",
    operation_description="Public API endpoint for creating categories without authentication, "
                          "designed for JavaScript modal forms that need to create categories.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'business_id'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description='Category name'),
            'business_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Business ID'),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description='Category description'),
            'category_type': openapi.Schema(type=openapi.TYPE_STRING, description='Category type (default: general)'),
            'is_top_level': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Whether this is a top-level category')
        }
    ),
    responses={
        200: openapi.Response('Successful response', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'slug': openapi.Schema(type=openapi.TYPE_STRING),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
                'category_type': openapi.Schema(type=openapi.TYPE_STRING),
                'is_top_level': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
            }
        )),
        400: 'Bad Request - Missing required fields or invalid data',
        404: 'Business not found',
        405: 'Method not allowed',
        500: 'Server error'
    },
    tags=['Categories']
)
def create_category(request):
    """
    Public endpoint for creating categories - no authentication required
    For use with JavaScript modal forms that need to create categories.
    """
    print("\n\n[PUBLIC_API] create_category called")
    
    # Only allow POST method
    if request.method != 'POST':
        print("[PUBLIC_API] Method not allowed")
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Print request data for debugging
    print(f"[PUBLIC_API] Headers: {dict(request.headers)}")
    
    try:
        # Parse JSON data
        data = json.loads(request.body)
        print(f"[PUBLIC_API] Request data: {data}")
        
        name = data.get('name')
        description = data.get('description', '')
        category_type = data.get('category_type', 'general')
        is_top_level = data.get('is_top_level', False)
        business_id = data.get('business_id')
        
        if not name:
            print("[PUBLIC_API] Name is required")
            return JsonResponse({'error': 'Category name is required'}, status=400)
            
        if not business_id:
            print("[PUBLIC_API] Business ID is required")
            return JsonResponse({'error': 'Business ID is required'}, status=400)
        
        # Get business
        try:
            business = Business.objects.get(id=business_id)
            print(f"[PUBLIC_API] Found business: {business.name} (ID: {business.id})")
        except Business.DoesNotExist:
            print(f"[PUBLIC_API] Business with ID {business_id} not found")
            return JsonResponse({'error': f'Business with ID {business_id} not found'}, status=404)
        
        # Create slug
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        
        # Make slug unique
        while Category.objects.filter(slug=slug, business=business).exists():
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            slug = f"{base_slug}-{random_suffix}"
            counter += 1
            if counter > 10:  # Safety limit
                break
        
        # Create category
        category = Category(
            name=name,
            slug=slug,
            description=description,
            category_type=category_type,
            business=business,
            is_top_level=is_top_level,
            is_active=True
        )
        category.save()
        print(f"[PUBLIC_API] Created category {category.name} (ID: {category.id})")
        
        # Return success response
        response_data = {
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'category_type': category.category_type,
            'is_top_level': category.is_top_level,
            'is_active': category.is_active
        }
        print(f"[PUBLIC_API] Returning: {response_data}")
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        print("[PUBLIC_API] Invalid JSON")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        import traceback
        print(f"[PUBLIC_API] Error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
