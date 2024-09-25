from django.db import models
from user_log.models import Account
from product_management.models import Product, Category
from django.utils import timezone


# Create your models here.

class Offer(models.Model):
    OFFER_TYPES = (
        ('product', 'Product Offer'),
        ('category', 'Category Offer'),
        # ('referral', 'Referral Offer'),
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

    def __str__(self):
        return self.name

class ProductOffer(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def apply_discount(self, price):
        if self.offer.is_valid():
            discount = price * (self.offer.discount_percentage / 100)
            return price - discount
        return price

    def __str__(self):
        return f"{self.offer.name} - {self.product.title}"
    


class CategoryOffer(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def apply_discount(self, price):
        if self.offer.is_valid():
            discount = price * (self.offer.discount_percentage / 100)
            return price - discount
        return price

    def __str__(self):
        return f"{self.offer.name} - {self.category.name}"

class ReferralOffer(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    referrer = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='referrer')
    referred = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='referred')
    is_claimed = models.BooleanField(default=False)

    def claim_offer(self):
        if not self.is_claimed and self.offer.is_valid():
            self.is_claimed = True
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.offer.name} - {self.referrer.username} -> {self.referred.username}"
