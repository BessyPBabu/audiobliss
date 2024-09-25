from django.db import models
from django.conf import settings
from product_management.models import ProductVariant
from decimal import Decimal




class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"
    
    def get_total_price(self):
        return Decimal(sum(item.subtotal for item in self.items.all()))
    
    def get_item_count(self):
        return self.items.count()

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product_variant')

    def __str__(self):
        return f"{self.quantity} x {self.product_variant} in cart for {self.cart.user.username}"

    @property
    def subtotal(self):
        return self.quantity * self.price_at_addition
    
    def save(self, *args, **kwargs):
        if not self.pk:  # If this is a new cart item
            product = self.product_variant.product
            best_offer = product.get_best_offer()
            if best_offer:
                self.price_at_addition = best_offer.apply_discount(self.product_variant.price)
            else:
                self.price_at_addition = self.product_variant.price
        super().save(*args, **kwargs)
    

class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wishlist for {self.user.username}"
    
    def get_item_count(self):
        return self.items.count()

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('wishlist', 'product_variant')

    def __str__(self):
        return f"{self.product_variant} in wishlist for {self.wishlist.user.username}"
    
    def save(self, *args, **kwargs):
        # Set the price when the item is first added to the wishlist
        if not self.pk:  # If this is a new wishlist item
            product = self.product_variant.product
            best_offer = product.get_best_offer()
            if best_offer:
                self.price_at_addition = best_offer.apply_discount(self.product_variant.price)
            else:
                self.price_at_addition = self.product_variant.price
        super().save(*args, **kwargs)
    