from django.shortcuts import render
from django.views.generic import TemplateView

def home(request):
    """Landing page view"""
    return render(request, 'website/home.html')

def about(request):
    """About page view"""
    return render(request, 'website/about.html')

def contact(request):
    """Contact page view"""
    return render(request, 'website/contact.html')

def services(request):
    """Services page view"""
    return render(request, 'website/services.html')

def pricing(request):
    """Pricing page view"""
    return render(request, 'website/pricing.html')
