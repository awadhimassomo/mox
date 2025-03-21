from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, OTPCredit, UserProfile,Kijiwe

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('phone', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'region')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('phone', 'email')
    ordering = ('phone',)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'region', 'created_at', 'updated_at')
    search_fields = ('user__phone', 'region')
    list_filter = ('region',)


class KijiweAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'created_at')
    search_fields = ('name', 'address')


class OTPCreditAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'otp_timestamp', 'otp_expiry', 'created_at', 'updated_at')  # ✅ Columns in the admin list view
    list_filter = ('created_at', 'otp_expiry')  # ✅ Filters
    search_fields = ('user__phone', 'otp')  # ✅ Enable search by user phone and OTP
    readonly_fields = ('created_at', 'updated_at', 'otp_timestamp', 'otp_expiry')  # ✅ Make timestamps read-only
    ordering = ('-created_at',)  # ✅ Order by newest OTPs
    
    
admin.register(OTPCredit)
class OTPCreditAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'otp_timestamp', 'otp_expiry', 'created_at', 'updated_at', 'is_expired')
    search_fields = ('user__phone', 'otp')
    list_filter = ('otp_expiry', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'otp_timestamp')

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = "Expired"

admin.site.register(Kijiwe, KijiweAdmin)
admin.site.register(OTPCredit,OTPCreditAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
