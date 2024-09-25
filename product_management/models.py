from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
from django.core.exceptions import ValidationError
import re
from django.utils.translation import gettext_lazy as gettext
from django.apps import apps

# Brand model (new)
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
def get_default_brand():
    Brand = apps.get_model('product_management', 'Brand')
    return Brand.objects.first().id if Brand.objects.exists() else None

# Category model
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name
    
# Product model
class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    brand = models.ForeignKey('Brand', on_delete=models.CASCADE) 
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['title'], name='unique_title', condition=models.Q(deleted=False)),
        ]
        ordering = ['id']

    def clean(self):
        # Check for title uniqueness, excluding the current instance
        if Product.objects.filter(title__iexact=self.title).exclude(pk=self.pk).exists():
            raise ValidationError("A product with this title already exists.")

        # Check if the associated category is active
        if not self.category.is_active:
            raise ValidationError("Cannot activate a product in an inactive category.")

    def __str__(self):
        return self.title
    
    def get_best_offer(self):
        from offer_management.models import ProductOffer, CategoryOffer
        
        product_offers = ProductOffer.objects.filter(product=self, offer__is_active=True)
        category_offers = CategoryOffer.objects.filter(category=self.category, offer__is_active=True)
        
        best_discount = 0
        best_offer = None

        for offer in product_offers:
            if offer.offer.is_valid() and offer.offer.discount_percentage > best_discount:
                best_discount = offer.offer.discount_percentage
                best_offer = offer

        for offer in category_offers:
            if offer.offer.is_valid() and offer.offer.discount_percentage > best_discount:
                best_discount = offer.offer.discount_percentage
                best_offer = offer

        return best_offer

    def get_discounted_price(self):
        best_offer = self.get_best_offer()
        if best_offer:
            if hasattr(best_offer, 'apply_discount'):
                return best_offer.apply_discount(self.variants.first().price)
        return self.variants.first().price

# Color model
class Color(models.Model):
    name = models.CharField(max_length=50)
    hex_code = models.CharField(max_length=7, null=True, blank=True)

    def clean(self):
        if self.hex_code and not re.match(r'^#[0-9A-Fa-f]{6}$', self.hex_code):
            raise ValidationError("Enter a valid hex color code (e.g., #FF0000).")

    def __str__(self):
        return f"{self.name} ({self.hex_code})"
    


# ProductVariant model
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    max_quantity_per_user = models.PositiveIntegerField(default=5)
    deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    image1 = ProcessedImageField(upload_to='static/admin/imgs',
                                 processors=[ResizeToFill(800, 800)],
                                 format='JPEG',
                                 options={'quality': 90},
                                 null=True, blank=True)
    image2 = ProcessedImageField(upload_to='static/admin/imgs',
                                 processors=[ResizeToFill(800, 800)],
                                 format='JPEG',
                                 options={'quality': 90},
                                 null=True, blank=True)
    image3 = ProcessedImageField(upload_to='static/admin/imgs',
                                 processors=[ResizeToFill(800, 800)],
                                 format='JPEG',
                                 options={'quality': 90},
                                 null=True, blank=True)

    class Meta:
        unique_together = ('product', 'color')
        ordering = ['id']

    def clean(self):
        if self.price is not None and self.price < 0:
            raise ValidationError("Price must be non-negative.")
        
        if self.stock is not None and self.stock < 0:
            raise ValidationError("Stock must be non-negative.")

        if self.price is None:
            raise ValidationError("Price cannot be None.")

        if self.stock is None:
            raise ValidationError("Stock cannot be None.")

        if self.is_active:
            if not self.product.is_active:
                raise ValidationError("Cannot activate a variant of an inactive product.")
            if not self.product.category.is_active:
                raise ValidationError("Cannot activate a variant of a product in an inactive category.")

    def __str__(self):
        return f'{self.product.title} - {self.color.name}'
