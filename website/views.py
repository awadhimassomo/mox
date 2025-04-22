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

def faq(request):
    """FAQ page view"""
    return render(request, 'website/faq.html')

def terms(request):
    """Terms of Service page view"""
    return render(request, 'website/terms.html')

def privacy(request):
    """Privacy Policy page view"""
    return render(request, 'website/privacy.html')
