from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_data_importer", "0003_load_inegi_base_layers"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataimportjob",
            name="layer_abstract",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="dataimportjob",
            name="layer_keywords",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Palabras clave separadas por coma",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="dataimportjob",
            name="layer_license",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Identificador de licencia (ej. CC-BY)",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="dataimportjob",
            name="layer_category",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Identificador de categoria topica GeoNode",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="dataimportjob",
            name="layer_attribution",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Fuente o propietario de los datos",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="dataimportjob",
            name="style_specs",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text="Lista de {col, type, palette, n_classes, classification}",
            ),
        ),
    ]
