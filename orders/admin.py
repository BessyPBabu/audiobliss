from django.contrib import admin
from .models import Order, OrderProduct, Payment
from user_log.models import Address

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_id', 'payment_method', 'created_at')
    search_fields = ('payment_id', 'payment_method')
    list_filter = ('payment_method', 'created_at')

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0
    readonly_fields = ('product_variant', 'quantity', 'product_price', 'sub_total')
    can_delete = False

class OrderAdmin(admin.ModelAdmin):
    def short_address(self, obj):
        if obj.address:
            return f"{obj.address.house_name}, {obj.address.place}"
        return "No address"
    short_address.short_description = 'Address'

    list_display = ('user', 'order_id', 'short_address', 'order_total', 'status', 'is_ordered', 'created_at', 'updated_at')
    list_filter = ('status', 'is_ordered', 'created_at', 'updated_at', 'address__state', 'address__district')
    search_fields = ('order_id', 'user__username', 'user__email', 'address__house_name', 'address__place')
    readonly_fields = ('order_id', 'user', 'order_total', 'tax', 'payment', 'is_ordered', 'created_at', 'updated_at')
    inlines = [OrderProductInline]

    fieldsets = (
        (None, {
            'fields': ('order_id', 'user', 'payment', 'address', 'order_note')
        }),
        ('Order Details', {
            'fields': ('order_total', 'tax', 'status', 'is_ordered', 'created_at', 'updated_at')
        }),
    )

class OrderProductAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_variant', 'quantity', 'product_price', 'sub_total', 'ordered', 'created_at', 'updated_at')
    list_filter = ('ordered', 'created_at', 'updated_at')
    search_fields = ('order__order_id', 'product_variant__product__title')

class AddressAdmin(admin.ModelAdmin):
    list_display = ('account', 'house_name', 'streat_name', 'place', 'district', 'state', 'pincode', 'is_default')
    list_filter = ('state', 'district', 'is_default')
    search_fields = ('account__username', 'account__email', 'house_name', 'place', 'pincode')

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct, OrderProductAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Address, AddressAdmin)