from django.contrib import admin
from .models import Category, Color, Product, ProductVariant

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'brand_name', 'category']
    search_fields = ['title', 'brand_name']

admin.site.register(Category)
admin.site.register(Color)
admin.site.register(ProductVariant)

