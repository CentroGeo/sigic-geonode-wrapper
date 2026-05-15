from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sigic_dashboard", "0002_site_is_public"),
    ]
    operations = [
        migrations.AddField(
            model_name="site",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True,
                null=True,
                blank=True,
                verbose_name="Fecha de creacion",
            ),
        ),
    ]
