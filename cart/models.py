import logging
from decimal import Decimal
from django.conf import settings
from django.db import models
from product_management.models import ProductVariant

logger = logging.getLogger(__name__)


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total(self):
        return sum(item.subtotal for item in self.items.select_related('product_variant').all())

    def get_item_count(self):
        return self.items.count()

    def clear(self):
        deleted, _ = self.items.all().delete()
        logger.info("Cleared %s items from cart %s", deleted, self.id)

    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        return self.quantity * self.price_at_addition

    def save(self, *args, **kwargs):
        # Set price at addition only when first created
        if not self.pk and self.price_at_addition == Decimal('0.00'):
            from services.offer_service import get_discounted_price_for_variant
            self.price_at_addition = get_discounted_price_for_variant(self.product_variant)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product_variant} in {self.cart}"

    class Meta:
        unique_together = ('cart', 'product_variant')


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_item_count(self):
        return self.items.count()

    def __str__(self):
        return f"Wishlist for {self.user.username}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    added_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.pk and self.price_at_addition == Decimal('0.00'):
            from services.offer_service import get_discounted_price_for_variant
            self.price_at_addition = get_discounted_price_for_variant(self.product_variant)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_variant} in wishlist for {self.wishlist.user.username}"

    class Meta:
        unique_together = ('wishlist', 'product_variant')
