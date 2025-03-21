from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0003_alter_customuser_options_customuser_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kijiwe',
            name='region',
            field=models.CharField(blank=True, choices=[('dar_es_salaam', 'Dar es Salaam'), ('arusha', 'Arusha'), ('mwanza', 'Mwanza'), ('dodoma', 'Dodoma'), ('tanga', 'Tanga'), ('mbeya', 'Mbeya'), ('morogoro', 'Morogoro'), ('zanzibar', 'Zanzibar')], max_length=50, null=True),
        ),
    ]
