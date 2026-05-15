from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_data_importer", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ineibaselayer",
            name="table_name",
            field=models.CharField(
                default="",
                help_text="Nombre de tabla en PostGIS geodata (ej. inegi_estados)",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="ineibaselayer",
            name="geonode_dataset_id",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
