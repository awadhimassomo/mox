from django.db import migrations

def assign_business_to_categories(apps, schema_editor):
    """Assign all categories without a business to the first business found"""
    Category = apps.get_model('business', 'Category')
    Business = apps.get_model('business', 'Business')
    
    # Get orphan categories
    orphan_categories = Category.objects.filter(business__isnull=True)
    
    if not orphan_categories.exists():
        # No orphan categories, nothing to do
        return
    
    # Try to find a business
    businesses = Business.objects.all()
    if not businesses.exists():
        # Create a default business if none exists
        # This is a fallback and should not happen in practice
        print("WARNING: No businesses found. Creating a default business.")
        User = apps.get_model('operations', 'CustomUser')
        users = User.objects.all()
        if users.exists():
            default_user = users.first()
            default_business = Business.objects.create(
                name="Default Business",
                owner=default_user,
                address="Default Address",
                phone="+255000000000"
            )
        else:
            raise Exception("No users found in the system. Cannot create default business.")
    else:
        default_business = businesses.first()
    
    # Update all orphan categories
    orphan_categories.update(business=default_business)
    print(f"Assigned {orphan_categories.count()} categories to business ID: {default_business.id}")

class Migration(migrations.Migration):
    dependencies = [
        ('business', '0010_category_business_alter_category_slug_and_more'),
    ]

    operations = [
        migrations.RunPython(assign_business_to_categories, migrations.RunPython.noop),
    ]
