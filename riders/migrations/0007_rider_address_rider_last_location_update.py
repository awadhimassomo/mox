# Generated by Django 4.2.14 on 2025-04-25 07:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('riders', '0006_rider_profile_image_alter_rider_transport_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='rider',
            name='address',
            field=models.TextField(blank=True, help_text='Human-readable address from reverse geocoding', null=True),
        ),
        migrations.AddField(
            model_name='rider',
            name='last_location_update',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
