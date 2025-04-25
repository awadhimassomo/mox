from django.db import models
from django.utils import timezone
from operations.models import CustomUser  # Import CustomUser from operations

class OTPVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="otp_verifications")
    otp = models.CharField(max_length=6)
    otp_timestamp = models.DateTimeField(auto_now_add=True)
    otp_expiry = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def is_expired(self):
        return timezone.now() > self.otp_expiry

    def __str__(self):
        return f"OTP for {self.user.phone} (Expires: {self.otp_expiry})"
