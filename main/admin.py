from django.contrib import admin
from .models import Partner, Consignment

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'partner_type', 'city', 'created_at')
    list_filter = ('partner_type', 'city')
    search_fields = ('name', 'email', 'city')

@admin.register(Consignment)
class ConsignmentAdmin(admin.ModelAdmin):
    list_display = ('consignment_number', 'origin', 'destination', 'status', 'updated_at')
    list_filter = ('status', 'origin', 'destination')
    search_fields = ('consignment_number',)