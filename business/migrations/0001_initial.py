# Generated by Django 4.2.13 on 2025-03-02 16:27

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('owner_name', models.CharField(blank=True, max_length=255, null=True)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('phone', models.CharField(blank=True, max_length=15, null=True)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('region', models.CharField(blank=True, choices=[('dar_es_salaam', 'Dar es Salaam'), ('arusha', 'Arusha'), ('mwanza', 'Mwanza'), ('dodoma', 'Dodoma'), ('tanga', 'Tanga'), ('mbeya', 'Mbeya'), ('morogoro', 'Morogoro'), ('zanzibar', 'Zanzibar')], max_length=50, null=True)),
                ('created_at', models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
            ],
            options={
                'verbose_name_plural': 'Businesses',
                'ordering': ['name'],
            },
        ),
    ]
