# Generated by Django 5.0.7 on 2024-09-14 12:53

from django.db import migrations


def populate_brand(apps, schema_editor):
    Product = apps.get_model('product_management', 'Product')
    Brand = apps.get_model('product_management', 'Brand')
    
    default_brand, _ = Brand.objects.get_or_create(name="Default Brand")
    
    for product in Product.objects.filter(brand__isnull=True):
        product.brand = default_brand
        product.save()


class Migration(migrations.Migration):

    dependencies = [
        ('product_management', '0015_auto_20240914_1814'),
    ]

    operations = [
        migrations.RunPython(populate_brand),
    ]
