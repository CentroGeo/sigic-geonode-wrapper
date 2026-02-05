# Migracion inicial: crea los 4 modelos de escenarios

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import sigic_geonode.sigic_scenarios.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Scenario ---
        migrations.CreateModel(
            name="Scenario",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Nombre del escenario",
                        max_length=256,
                        verbose_name="Nombre",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scenarios",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Propietario",
                    ),
                ),
                (
                    "url_id",
                    models.CharField(
                        blank=True, max_length=255, null=True, unique=True
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=False,
                        help_text="Si esta marcado, el escenario sera visible para todos los usuarios.",
                        verbose_name="Publico",
                    ),
                ),
                (
                    "card_image",
                    models.ImageField(
                        blank=True,
                        help_text="Imagen que representa el escenario",
                        null=True,
                        upload_to="scenarios/cards/",
                        verbose_name="Imagen de portada",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Descripcion detallada del escenario",
                        null=True,
                        verbose_name="Descripcion",
                    ),
                ),
                (
                    "scenes_layout_styles",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Configuracion del layout de las escenas",
                        verbose_name="Estilos de layout",
                    ),
                ),
            ],
            options={
                "db_table": "sigic_scenarios",
                "verbose_name": "Escenario",
                "verbose_name_plural": "Escenarios",
                "ordering": ["-created_at"],
            },
        ),
        # --- Scene ---
        migrations.CreateModel(
            name="Scene",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Nombre de la escena",
                        max_length=256,
                        verbose_name="Nombre",
                    ),
                ),
                (
                    "scenario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scenes",
                        to="sigic_scenarios.scenario",
                    ),
                ),
                (
                    "map_center_lat",
                    models.FloatField(blank=True, null=True),
                ),
                (
                    "map_center_long",
                    models.FloatField(blank=True, null=True),
                ),
                (
                    "zoom",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "text_position",
                    models.CharField(
                        choices=[("left", "Izquierda"), ("right", "Derecha")],
                        default="left",
                        help_text="Posicion del texto dentro de una escena",
                        max_length=5,
                        verbose_name="Posicion del texto",
                    ),
                ),
                (
                    "text_content",
                    models.TextField(
                        blank=True,
                        help_text="Texto HTML de la escena",
                        null=True,
                        verbose_name="Contenido",
                    ),
                ),
                (
                    "styles",
                    models.JSONField(
                        blank=True,
                        default=sigic_geonode.sigic_scenarios.models.default_scene_styles,
                        null=True,
                        verbose_name="Estilo de la escena",
                    ),
                ),
                ("stack_order", models.IntegerField(default=0)),
            ],
            options={
                "db_table": "sigic_scenes",
                "verbose_name": "Escena",
                "verbose_name_plural": "Escenas",
                "ordering": ["stack_order"],
            },
        ),
        # --- SceneLayer ---
        migrations.CreateModel(
            name="SceneLayer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "scene",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="layers",
                        to="sigic_scenarios.scene",
                    ),
                ),
                (
                    "geonode_id",
                    models.IntegerField(
                        blank=True,
                        db_index=True,
                        help_text="ID de referencia de la capa en GeoNode",
                        null=True,
                        verbose_name="ID de la capa en GeoNode",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Nombre tecnico de la capa en GeoServer",
                        max_length=256,
                        verbose_name="Nombre de la capa (typename)",
                    ),
                ),
                (
                    "style",
                    models.CharField(
                        blank=True,
                        help_text="Nombre del estilo aplicado a la capa",
                        max_length=256,
                        null=True,
                        verbose_name="Nombre del estilo",
                    ),
                ),
                (
                    "style_title",
                    models.CharField(
                        blank=True,
                        help_text="Titulo del estilo aplicado a la capa",
                        max_length=256,
                        null=True,
                        verbose_name="Titulo del estilo",
                    ),
                ),
                (
                    "visible",
                    models.BooleanField(
                        default=True,
                        help_text="Si la capa esta visible en el mapa",
                        verbose_name="Visible",
                    ),
                ),
                (
                    "opacity",
                    models.FloatField(
                        default=1.0,
                        help_text="Opacidad de la capa (0.0 a 1.0)",
                        verbose_name="Opacidad",
                    ),
                ),
                (
                    "stack_order",
                    models.IntegerField(
                        default=0,
                        help_text="Orden de las capas en el mapa (mayor = arriba)",
                        verbose_name="Orden de apilamiento",
                    ),
                ),
            ],
            options={
                "db_table": "sigic_scene_layers",
                "verbose_name": "Capa de escena",
                "verbose_name_plural": "Capas de escena",
                "ordering": ["stack_order"],
            },
        ),
        # --- SceneMarker ---
        migrations.CreateModel(
            name="SceneMarker",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "scene",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="markers",
                        to="sigic_scenarios.scene",
                    ),
                ),
                (
                    "lat",
                    models.DecimalField(
                        decimal_places=10,
                        max_digits=19,
                        verbose_name="Latitud",
                    ),
                ),
                (
                    "lng",
                    models.DecimalField(
                        decimal_places=10,
                        max_digits=19,
                        verbose_name="Longitud",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="Titulo",
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Contenido del marcador",
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        default="fas fa-map-marker-alt",
                        help_text="Clase de Font Awesome",
                        max_length=50,
                        verbose_name="Icono",
                    ),
                ),
                (
                    "color",
                    models.CharField(
                        default="#ec4899",
                        help_text="Color hexadecimal",
                        max_length=7,
                        verbose_name="Color del marcador",
                    ),
                ),
                (
                    "image_url",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "options",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Opciones adicionales en formato JSON",
                        null=True,
                        verbose_name="Opciones del marcador",
                    ),
                ),
            ],
            options={
                "db_table": "sigic_scene_markers",
                "verbose_name": "Marcador de escena",
                "verbose_name_plural": "Marcadores de escena",
                "ordering": ["id"],
            },
        ),
    ]
