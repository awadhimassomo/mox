from django.contrib import admin

from riders.models import Rider

# Register your models here.

class RiderAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone_number', 'region', 'is_available', 'created_at')
    search_fields = ('phone_number', 'first_name', 'last_name')
    list_filter = ('region', 'is_available')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(Rider, RiderAdmin)