from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0054_alter_service_type"),
    ]

    operations = [
        # 1. Quita unique=True del campo base_url
        migrations.AlterField(
            model_name="service",
            name="base_url",
            field=models.URLField(db_index=True),
        ),
        # 2. Agrega constraint por usuario
        migrations.AddConstraint(
            model_name="service",
            constraint=models.UniqueConstraint(
                fields=("base_url", "owner"),
                name="services_unique_baseurl_per_user",
            ),
        ),
    ]
