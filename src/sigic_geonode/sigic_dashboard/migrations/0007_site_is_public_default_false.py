from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_dashboard", "0006_indicator_general_values"),
    ]

    operations = [
        migrations.AlterField(
            model_name="site",
            name="is_public",
            field=models.BooleanField(
                default=False,
                help_text="Si es verdadero el tablero es visible para todos los usuarios",
                verbose_name="Público",
            ),
        ),
    ]
