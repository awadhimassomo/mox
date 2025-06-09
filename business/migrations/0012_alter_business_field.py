from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('business', '0011_assign_business_to_categories'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='business',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='categories',
                to='business.business'
            ),
        ),
    ]
