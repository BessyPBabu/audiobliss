# Generated by Django 5.0.7 on 2024-08-08 06:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_management', '0006_alter_category_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='color',
            name='name',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted', False)), fields=('title',), name='unique_title'),
        ),
    ]
