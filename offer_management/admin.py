from django.contrib import admin
from .models import Offer, ProductOffer, CategoryOffer

class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'offer_type', 'discount_percentage', 'start_date', 'end_date', 'is_active')
    list_filter = ('offer_type', 'is_active', 'start_date', 'end_date')
    search_fields = ('name', 'description')

class ProductOfferAdmin(admin.ModelAdmin):
    list_display = ('offer', 'product')
    list_filter = ('offer', 'product')
    search_fields = ('offer__name', 'product__name')

class CategoryOfferAdmin(admin.ModelAdmin):
    list_display = ('offer', 'category')
    list_filter = ('offer', 'category')
    search_fields = ('offer__name', 'category__name')



admin.site.register(Offer, OfferAdmin)
admin.site.register(ProductOffer, ProductOfferAdmin)
admin.site.register(CategoryOffer, CategoryOfferAdmin)

