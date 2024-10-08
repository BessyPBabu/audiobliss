# Generated by Django 5.0.7 on 2024-08-17 06:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_management', '0012_remove_product_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='product',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
