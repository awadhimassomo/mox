from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'business'

urlpatterns = [
    path('list/', views.business_list, name='business_list'),
    path('api/data/', views.get_businesses_data, name='get_businesses_data'),
    path('register/', views.business_register, name='business_register'),  # Business Registration URL
    path('login/', views.business_login, name='business_login'),
    path('logout/', LogoutView.as_view(next_page='business:business_login'), name='logout'),
    path('sales-history/', views.sales_history, name='sales_history'),
    path('earnings/', views.earnings, name='earnings'),
    path('profile/', views.business_profile, name='profile'),
    path('dashboard/', views.business_dashboard, name='business_dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('create-business/', views.create_business, name='create_business'),
    path('mark-order-ready/', views.mark_order_ready, name='mark_order_ready'),
]
