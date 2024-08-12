from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
from django.core.exceptions import ValidationError
import re




# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100,unique=True)
    description = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name
    
 
class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    brand_name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)

    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['title'], name='unique_title', condition=models.Q(deleted=False)),
        ]
        ordering = ['id']

    def clean(self):
        if Product.objects.filter(title__iexact=self.title).exclude(id=self.id).exists():
            raise ValidationError("Product with this title already exists.")

    def __str__(self):
        return self.title

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

    def __str__(self):
        return f'{self.product.title} - {self.color.name}'