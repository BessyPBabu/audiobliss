from django.contrib import admin
from .models import Category, Color, Product, ProductVariant, Brand

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'brand', 'category']
    search_fields = ['title', 'brand']

admin.site.register(Category)
admin.site.register(Color)
admin.site.register(ProductVariant)
admin.site.register(Brand)

