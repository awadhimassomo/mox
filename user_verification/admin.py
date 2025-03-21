from .models import OTPVerification
from django.contrib import admin

class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'otp_timestamp', 'otp_expiry', 'is_expired')  # ✅ Show these fields in the list
    search_fields = ('user__phone', 'otp')  # ✅ Allow search by user phone or OTP
    list_filter = ('otp_expiry',)  # ✅ Add filter by expiry date
    readonly_fields = ('otp_timestamp', 'otp_expiry')  # ✅ Make timestamps read-only

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True 
    

admin.site.register(OTPVerification, OTPVerificationAdmin)