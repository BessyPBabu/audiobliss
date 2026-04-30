import logging
from decimal import Decimal
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('amount', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expiration_date = models.DateTimeField()
    active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def is_valid(self):
        return self.active and self.expiration_date > timezone.now()

    def is_applicable_for(self, cart_total):
        cart_total = Decimal(str(cart_total))
        if not self.is_valid():
            return False, "Coupon has expired or is inactive."
        if self.min_purchase_amount and cart_total < self.min_purchase_amount:
            return False, f"Minimum purchase of ₹{self.min_purchase_amount} required."
        return True, ""

    def calculate_discount(self, cart_total):
        from decimal import ROUND_HALF_UP
        cart_total = Decimal(str(cart_total))
        if self.discount_type == 'percentage':
            return (cart_total * self.discount_value / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        return min(self.discount_value, cart_total).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE, related_name='coupon_usages'
    )
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True)
    code = models.CharField(max_length=50)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One coupon per order — prevents duplicate records
        unique_together = ('order', 'coupon')

    def __str__(self):
        return f"{self.code} on order {self.order_id}"
