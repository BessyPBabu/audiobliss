# Generated by Django 5.0.7 on 2024-08-08 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_management', '0007_alter_color_name_product_unique_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
    ]
