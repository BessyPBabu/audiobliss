from django.contrib import admin
from .models import Category, Color, Product, ProductVariant, Brand


class NotDeletedFilterMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        deleted_field = getattr(self.model, 'deleted', None)
        if deleted_field is not None:
            return qs.filter(deleted=False)
        is_deleted_field = getattr(self.model, 'is_deleted', None)
        if is_deleted_field is not None:
            return qs.filter(is_deleted=False)
        return qs


@admin.register(Product)
class ProductAdmin(NotDeletedFilterMixin, admin.ModelAdmin):
    list_display = ('title', 'brand', 'category', 'is_active')
    list_filter = ('is_active', 'category', 'brand')
    search_fields = ('title', 'brand__name', 'category__name')


@admin.register(Category)
class CategoryAdmin(NotDeletedFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Brand)
class BrandAdmin(NotDeletedFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')
    search_fields = ('name',)


@admin.register(ProductVariant)
class ProductVariantAdmin(NotDeletedFilterMixin, admin.ModelAdmin):
    list_display = ('product', 'color', 'price', 'stock', 'is_active')
    list_filter = ('is_active', 'product__category')
    search_fields = ('product__title', 'color__name')