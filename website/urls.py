from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('services/', views.services, name='services'),
    path('pricing/', views.pricing, name='pricing'),
    path('faq', views.faq, name='faq'),
    path('terms', views.terms, name='terms'),
    path('privacy-policy', views.privacy, name='privacy'),
]
