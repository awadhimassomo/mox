from django.urls import path
from .views import request_otp, resend_otp, verify_otp_view

app_name='user_verification'

urlpatterns = [
    path('request-otp/', request_otp, name='request_otp'),
    path('verify-otp/', verify_otp_view, name='verify_otp'),
    path('resend-otp/', resend_otp, name='resend_otp'),
]
