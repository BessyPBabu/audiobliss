import logging
from decimal import Decimal
from django.db import models
from user_log.models import Account, Address
from product_management.models import ProductVariant

logger = logging.getLogger(__name__)


class Payment(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    status = models.CharField(max_length=100, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.payment_id


class Order(models.Model):
    STATUS_CHOICES = (
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
        ('payment pending', 'Payment Pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Pending Cancellation', 'Pending Cancellation'),
        ('Cancelled', 'Cancelled'),
        ('Return Requested', 'Return Requested'),
        ('Returned', 'Returned'),
    )

    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    payment_status = models.CharField(max_length=100, default='Pending')
    order_id = models.CharField(max_length=100, unique=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    order_note = models.CharField(max_length=100, blank=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0'))
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='New')
    ip = models.CharField(blank=True, max_length=20)
    is_ordered = models.BooleanField(default=False)
    is_refunded = models.BooleanField(default=False)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    cancel_reason = models.TextField(null=True, blank=True)
    is_cancel_requested = models.BooleanField(default=False)
    is_cancel_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return self.order_total + self.tax - self.coupon_discount

    def can_be_cancelled(self):
        return self.status in ('New', 'Confirmed')

    def can_be_returned(self):
        return self.status == 'Delivered'

    def mark_as_delivered(self):
        self.status = 'Delivered'
        self.save(update_fields=['status'])
        logger.info("Order %s marked as delivered", self.order_id)

    def __str__(self):
        return f"Order {self.order_id} by {self.user.username}"

    class Meta:
        ordering = ['-created_at']


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_products')
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def sub_total(self):
        return self.product_price * self.quantity

    def __str__(self):
        return f"{self.product_variant.product.title} x{self.quantity}"


class ReturnRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    refunded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_pending(self):
        return self.status == 'Pending'

    def __str__(self):
        return f"Return for Order #{self.order.id} - {self.status}"
