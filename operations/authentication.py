from django.contrib.auth.backends import ModelBackend
from operations.models import CustomUser

class PhoneAuthBackend(ModelBackend):
    """Authenticate users using their phone number instead of username."""
    def authenticate(self, request, phone=None, password=None, **kwargs):
        try:
            user = CustomUser.objects.get(phone=phone)
            if user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            return None
