import logging
from decimal import Decimal
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class Offer(models.Model):
    OFFER_TYPES = (
        ('product', 'Product Offer'),
        ('category', 'Category Offer'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField()
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPES)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=['is_active'])
        logger.info("Deactivated offer %s", self.id)

    def __str__(self):
        return self.name


class ProductOffer(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='product_offers')
    product = models.ForeignKey(
        'product_management.Product', on_delete=models.CASCADE, related_name='product_offers'
    )

    def apply_discount(self, price):
        if not self.offer.is_valid():
            return Decimal(str(price))
        price = Decimal(str(price))
        discount = price * (self.offer.discount_percentage / Decimal('100'))
        return (price - discount).quantize(Decimal('0.01'))

    def __str__(self):
        return f"{self.offer.name} - {self.product.title}"


class CategoryOffer(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='category_offers')
    category = models.ForeignKey(
        'product_management.Category', on_delete=models.CASCADE, related_name='category_offers'
    )

    def apply_discount(self, price):
        if not self.offer.is_valid():
            return Decimal(str(price))
        price = Decimal(str(price))
        discount = price * (self.offer.discount_percentage / Decimal('100'))
        return (price - discount).quantize(Decimal('0.01'))

    def __str__(self):
        return f"{self.offer.name} - {self.category.name}"
