# Generated by Django 4.2.14 on 2025-03-04 20:13

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('gas_type', models.CharField(choices=[('lpg', 'LPG'), ('natural', 'Natural Gas'), ('propane', 'Propane'), ('butane', 'Butane')], max_length=20)),
                ('tank_size', models.IntegerField(choices=[(6, '6 KG'), (13, '13 KG'), (15, '15 KG'), (38, '38 KG'), (45, '45 KG')])),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stock_quantity', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='business.business')),
            ],
            options={
                'ordering': ['name', 'tank_size'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('delivery_address', models.CharField(max_length=255)),
                ('delivery_latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('delivery_longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('in_transit', 'In Transit'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gas_orders', to='business.business')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='business.product')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
