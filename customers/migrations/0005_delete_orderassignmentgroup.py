# Generated by Django 4.2.14 on 2025-03-08 19:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0004_orderassignmentgroup_favorite'),
    ]

    operations = [
        migrations.DeleteModel(
            name='OrderAssignmentGroup',
        ),
    ]
