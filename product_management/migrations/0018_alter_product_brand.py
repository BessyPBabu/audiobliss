# Generated by Django 5.0.7 on 2024-09-14 17:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_management', '0017_alter_product_brand'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='brand',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product_management.brand'),
        ),
    ]
