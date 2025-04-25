from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError
from .models import CustomUser, normalize_phone_number
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class PhoneNumberAuthenticationBackend(ModelBackend):
    """
    Custom authentication backend for phone number authentication.
    Handles phone number normalization and account lockout.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user with phone number (as username) and password
        
        This method:
        1. Normalizes the phone number in various formats
        2. Checks if the account is locked due to failed attempts
        3. Implements proper password verification
        4. Updates failed login counters
        """
        if not username or not password:
            return None
            
        # Phone number is passed as username
        phone = username
        
        try:
            # Try to find the user with the normalized phone number
            try:
                normalized_phone = normalize_phone_number(phone)
                user = CustomUser.objects.get(phone=normalized_phone)
            except (CustomUser.DoesNotExist, ValidationError):
                # Try to find by alternate formats using our utility method
                try:
                    user = CustomUser.objects.get_by_phone(phone)
                except CustomUser.DoesNotExist:
                    # No user found with any phone format
                    logger.info(f"Failed login: user with phone {phone} not found")
                    return None
            
            # Check if account is locked
            if user.is_account_locked():
                logger.warning(f"Login attempt for locked account: {user.phone}")
                return None
            
            # Check password
            if user.check_password(password):
                # Reset failed login attempts on successful login
                user.reset_failed_login()
                
                # Update last login time
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                logger.info(f"Successful login for user {user.phone}")
                return user
            else:
                # Incorrect password
                user.increment_failed_login()
                logger.warning(f"Failed login attempt for user {user.phone}: incorrect password")
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None

    def get_user(self, user_id):
        """
        Get a user by their primary key ID
        """
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
