# Generated by Django 5.0.7 on 2024-08-04 22:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_orderaddress_is_default'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderaddress',
            name='is_default',
        ),
    ]
