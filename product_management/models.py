import re
import logging
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

logger = logging.getLogger(__name__)


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.save(update_fields=['is_deleted', 'is_active'])
        logger.info("Soft deleted brand %s", self.id)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.save(update_fields=['is_deleted', 'is_active'])
        # Cascade deactivate products
        self.product_set.filter(deleted=False).update(is_active=False)
        logger.info("Soft deleted category %s and deactivated related products", self.id)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def clean(self):
        if not self.category.is_active:
            raise ValidationError("Cannot activate a product in an inactive category.")
        if not self.brand.is_active:
            raise ValidationError("Cannot activate a product with an inactive brand.")

    def soft_delete(self):
        self.deleted = True
        self.is_active = False
        self.save(update_fields=['deleted', 'is_active'])
        self.variants.filter(deleted=False).update(deleted=True, is_active=False)
        logger.info("Soft deleted product %s and its variants", self.id)

    def get_best_offer(self):
        from services.offer_service import get_best_offer_for_product
        return get_best_offer_for_product(self)

    def get_discounted_price(self):
        from services.offer_service import get_discounted_price_for_variant
        first_variant = self.variants.filter(is_active=True, deleted=False).first()
        if first_variant:
            return get_discounted_price_for_variant(first_variant)
        return None

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['title'], name='unique_title', condition=models.Q(deleted=False)
            )
        ]


class Color(models.Model):
    name = models.CharField(max_length=50)
    hex_code = models.CharField(max_length=7, null=True, blank=True)

    def clean(self):
        if self.hex_code and not re.match(r'^#[0-9A-Fa-f]{6}$', self.hex_code):
            raise ValidationError("Enter a valid hex color code (e.g., #FF0000).")

    def __str__(self):
        return f"{self.name} ({self.hex_code})"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    max_quantity_per_user = models.PositiveIntegerField(default=5)
    deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    image1 = ProcessedImageField(
        upload_to='products/',
        processors=[ResizeToFill(800, 800)],
        format='JPEG',
        options={'quality': 90},
        null=True, blank=True,
    )
    image2 = ProcessedImageField(
        upload_to='products/',
        processors=[ResizeToFill(800, 800)],
        format='JPEG',
        options={'quality': 90},
        null=True, blank=True,
    )
    image3 = ProcessedImageField(
        upload_to='products/',
        processors=[ResizeToFill(800, 800)],
        format='JPEG',
        options={'quality': 90},
        null=True, blank=True,
    )

    def clean(self):
        if self.price is not None and self.price < 0:
            raise ValidationError("Price must be non-negative.")
        if self.is_active:
            if not self.product.is_active:
                raise ValidationError("Cannot activate a variant of an inactive product.")
            if not self.product.category.is_active:
                raise ValidationError("Cannot activate a variant in an inactive category.")

    def soft_delete(self):
        self.deleted = True
        self.is_active = False
        self.save(update_fields=['deleted', 'is_active'])
        logger.info("Soft deleted variant %s", self.id)

    def is_in_stock(self):
        return self.stock > 0

    def get_discounted_price(self):
        from services.offer_service import get_discounted_price_for_variant
        return get_discounted_price_for_variant(self)

    def reduce_stock(self, quantity):
        if self.stock < quantity:
            raise ValueError(
                f"Insufficient stock for {self.product.title}. Available: {self.stock}"
            )
        self.stock -= quantity
        self.save(update_fields=['stock'])
        logger.info("Reduced stock for variant %s by %s. Remaining: %s", self.id, quantity, self.stock)

    def __str__(self):
        return f"{self.product.title} - {self.color.name}"

    class Meta:
        unique_together = ('product', 'color')
        ordering = ['id']
