from django.contrib import admin
from .models import Coupon , CouponUsage

# coupon/admin.py
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_purchase_amount', 'expiration_date', 'active')
    search_fields = ('code',)
    list_filter = ('discount_type', 'active', 'expiration_date')
    ordering = ('-expiration_date',)

class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('order', 'coupon', 'code', 'discount_amount', 'applied_at')  # Fields to display in list view
    search_fields = ('code', 'order__id', 'coupon__code')  # Fields to search by
    list_filter = ('applied_at', 'coupon')  # Add filters for easy access
    
admin.site.register(CouponUsage, CouponUsageAdmin)