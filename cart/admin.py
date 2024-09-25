from django.contrib import admin
from cart.models import Cart, CartItem
from .models import Wishlist, WishlistItem

# Register your models here.

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]

class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product_variant', 'quantity', 'added_at', 'updated_at')
    list_filter = ('cart__user', 'product_variant__product__category')
    search_fields = ('cart__user__username', 'product_variant__product__title')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product_variant',)
    search_fields = ('product_variant__name',)
    list_filter = ('wishlist',)

admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem, CartItemAdmin)