# Generated by Django 5.0.7 on 2024-09-24 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0015_returnrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='returnrequest',
            name='refunded',
            field=models.BooleanField(default=False),
        ),
    ]
