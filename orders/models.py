from django.db import models
from user_log.models import Account, Address
from product_management.models import ProductVariant

# Create your models here.

# Model for storing payment information
class Payment(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    status = models.CharField(max_length=100,default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.payment_id

class Order(models.Model):
    STATUS = (
        ('New', 'New'),
        ('Confirmed', 'Confirmed'),
        ('payment pending', 'payment pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
    )
    
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True)
    payment_status = models.CharField(max_length=100, default='Pending')
    order_id = models.CharField(max_length=100)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True) 
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)  
    order_note = models.CharField(max_length=100, blank=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)  
    tax = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)  
    status = models.CharField(max_length=50, choices=STATUS, default='New')
    ip = models.CharField(blank=True, max_length=20)
    is_ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_refunded = models.BooleanField(default=False)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cancel_reason = models.TextField(null=True, blank=True)
    is_cancel_requested = models.BooleanField(default=False)
    is_cancel_confirmed = models.BooleanField(default=False)
    

    @property
    def total_amount(self):
        return self.order_total + self.tax - self.coupon_discount

    def update_totals(self):
        order_products = self.orderproduct_set.all()
        self.order_total = sum(item.sub_total() for item in order_products)
        self.save()

    def apply_coupon(self, discount_amount):
        self.coupon_discount = min(discount_amount, self.order_total)
        self.save()

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

# Model for storing details of products in an order
class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
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
        return f"{self.product_variant.product.title} - {self.product_variant.color.name} ({self.quantity} units)"



class ReturnRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    refunded = models.BooleanField(default=False)

    def __str__(self):
        return f"Return request for Order #{self.order.id} - {self.status}"