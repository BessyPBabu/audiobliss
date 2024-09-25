from django.db import models
from django.utils import timezone
from orders.models import Order

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
        now = timezone.now()
        return self.active and self.expiration_date > now

    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='coupon_usages')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True)
    code = models.CharField(max_length=50)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} used on order {self.order.id}"