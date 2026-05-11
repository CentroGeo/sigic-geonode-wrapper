from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sigic_dashboard", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="site",
            name="is_public",
            field=models.BooleanField(
                default=True,
                help_text="Si es verdadero el tablero es visible para todos los usuarios",
                verbose_name="Público",
            ),
        ),
    ]
