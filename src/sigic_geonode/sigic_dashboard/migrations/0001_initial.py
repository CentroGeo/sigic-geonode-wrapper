# Migracion inicial: crea los modelos del dashboard de indicadores

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("layers", "0044_alter_dataset_unique_together"),
    ]

    operations = [
        # --- Site ---
        migrations.CreateModel(
            name="Site",
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
                        help_text="Nombre corto para identificar rapidamente el sitio",
                        max_length=250,
                        unique=True,
                        verbose_name="Nombre del sitio",
                    ),
                ),
                (
                    "info_text",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Informacion de sitio",
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=500, verbose_name="Titulo del sitio"),
                ),
                (
                    "subtitle",
                    models.CharField(max_length=500, verbose_name="Subtitulo del sitio"),
                ),
                (
                    "url",
                    models.CharField(max_length=500, verbose_name="URL del sitio"),
                ),
            ],
            options={
                "db_table": "sigic_dashboard_site",
                "ordering": ["name"],
            },
        ),
        # --- SiteLogos ---
        migrations.CreateModel(
            name="SiteLogos",
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
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logos",
                        to="sigic_dashboard.site",
                    ),
                ),
                (
                    "icon",
                    models.ImageField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to="dashboard/logos/",
                        verbose_name="Logo",
                    ),
                ),
                (
                    "icon_link",
                    models.URLField(
                        blank=True,
                        default="",
                        verbose_name="Link del logo",
                    ),
                ),
                ("stack_order", models.IntegerField(default=1)),
            ],
            options={
                "db_table": "sigic_dashboard_site_logos",
                "ordering": ["stack_order"],
            },
        ),
        # --- IndicatorGroup ---
        migrations.CreateModel(
            name="IndicatorGroup",
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
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="groups",
                        to="sigic_dashboard.site",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=250,
                        verbose_name="Nombre del grupo de indicadores",
                    ),
                ),
                (
                    "info_text",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Informacion de grupo",
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        max_length=250, verbose_name="Descripcion del grupo"
                    ),
                ),
                ("stack_order", models.IntegerField(default=1)),
            ],
            options={
                "db_table": "sigic_dashboard_indicator_group",
                "ordering": ["stack_order"],
            },
        ),
        # --- SubGroup ---
        migrations.CreateModel(
            name="SubGroup",
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
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subgroups",
                        to="sigic_dashboard.indicatorgroup",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=250,
                        verbose_name="Nombre del subgrupo de indicadores",
                    ),
                ),
                (
                    "info_text",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Informacion de subgrupo",
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Clase CSS de Font Awesome (e.g. 'fas fa-chart-bar')",
                        max_length=100,
                        verbose_name="Icono del subgrupo",
                    ),
                ),
                (
                    "icon_custom",
                    models.ImageField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to="dashboard/subgroups/",
                        verbose_name="Icono personalizado del subgrupo",
                    ),
                ),
                ("stack_order", models.IntegerField(default=1)),
            ],
            options={
                "db_table": "sigic_dashboard_subgroup",
                "ordering": ["stack_order"],
            },
        ),
        # --- Indicator ---
        migrations.CreateModel(
            name="Indicator",
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
                    "subgroup",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="indicators",
                        to="sigic_dashboard.subgroup",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="indicators",
                        to="sigic_dashboard.indicatorgroup",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="indicators",
                        to="sigic_dashboard.site",
                    ),
                ),
                (
                    "layer",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="layers.dataset",
                        verbose_name="Capa de indicador",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=250, verbose_name="Nombre del indicador"),
                ),
                (
                    "plot_type",
                    models.CharField(max_length=250, verbose_name="Tipo de grafica"),
                ),
                (
                    "info_text",
                    models.TextField(
                        blank=True, null=True, verbose_name="Informacion de indicador"
                    ),
                ),
                (
                    "layer_id_field",
                    models.CharField(
                        max_length=550,
                        verbose_name="Campo id para identificar geometrias de la capa",
                    ),
                ),
                (
                    "layer_nom_field",
                    models.CharField(
                        blank=True,
                        max_length=550,
                        null=True,
                        verbose_name="Campo para nombrar geometrias de la capa",
                    ),
                ),
                (
                    "high_values_percentage",
                    models.IntegerField(
                        blank=True,
                        default=10,
                        null=True,
                        verbose_name="Porcentaje de geometrias a recuperar",
                    ),
                ),
                (
                    "use_single_field",
                    models.BooleanField(
                        default=False,
                        verbose_name="Generar grafica con un solo campo",
                    ),
                ),
                (
                    "is_histogram",
                    models.BooleanField(
                        default=False, verbose_name="Indicador de histograma"
                    ),
                ),
                (
                    "histogram_fields",
                    models.JSONField(
                        blank=True,
                        null=True,
                        verbose_name="Campos para generar el histograma",
                    ),
                ),
                (
                    "field_one",
                    models.CharField(max_length=550, verbose_name="Campo 1"),
                ),
                (
                    "field_two",
                    models.CharField(
                        blank=True, max_length=550, null=True, verbose_name="Campo 2"
                    ),
                ),
                (
                    "field_popup",
                    models.JSONField(
                        blank=True,
                        null=True,
                        verbose_name="Campos para desplegar info en el popup",
                    ),
                ),
                (
                    "category_method",
                    models.CharField(
                        blank=True,
                        max_length=250,
                        null=True,
                        verbose_name="Metodo de clasificacion",
                    ),
                ),
                (
                    "field_category",
                    models.IntegerField(
                        blank=True,
                        default=5,
                        null=True,
                        verbose_name="Numero de categorias para grafica",
                    ),
                ),
                (
                    "colors",
                    models.CharField(
                        blank=True,
                        max_length=250,
                        null=True,
                        verbose_name="Colores de grafico y tematizacion",
                    ),
                ),
                (
                    "use_custom_colors",
                    models.BooleanField(
                        default=False, verbose_name="Usar colores provistos por el cliente"
                    ),
                ),
                (
                    "custom_colors",
                    models.CharField(
                        blank=True,
                        max_length=250,
                        null=True,
                        verbose_name="Colores custom de grafico y tematizacion",
                    ),
                ),
                (
                    "plot_config",
                    models.JSONField(
                        blank=True,
                        null=True,
                        verbose_name="Configuracion para la grafica",
                    ),
                ),
                (
                    "plot_values",
                    models.JSONField(
                        blank=True, null=True, verbose_name="Valores para la grafica"
                    ),
                ),
                (
                    "map_values",
                    models.JSONField(
                        blank=True,
                        null=True,
                        verbose_name="Valores para tematizacion de la capa",
                    ),
                ),
                (
                    "show_general_values",
                    models.BooleanField(
                        default=False, verbose_name="Mostrar valores generales"
                    ),
                ),
                (
                    "use_filter",
                    models.BooleanField(default=False, verbose_name="Activar filtro"),
                ),
                (
                    "filters",
                    models.JSONField(blank=True, null=True, verbose_name="Filtros"),
                ),
                ("stack_order", models.IntegerField(default=1)),
            ],
            options={
                "db_table": "sigic_dashboard_indicator",
                "ordering": ["stack_order"],
            },
        ),
        # --- IndicatorFieldBoxInfo ---
        migrations.CreateModel(
            name="IndicatorFieldBoxInfo",
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
                    "indicator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="infoboxes",
                        to="sigic_dashboard.indicator",
                    ),
                ),
                (
                    "field",
                    models.CharField(
                        max_length=550, verbose_name="Campo de informacion"
                    ),
                ),
                (
                    "is_percentage",
                    models.BooleanField(
                        default=False, verbose_name="Es de porcentaje?"
                    ),
                ),
                (
                    "field_percentage_total",
                    models.CharField(
                        blank=True,
                        max_length=550,
                        null=True,
                        verbose_name="Campo total para calcular porcentaje",
                    ),
                ),
                ("name", models.CharField(max_length=550, verbose_name="Nombre del campo")),
                (
                    "icon",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Clase CSS de Font Awesome",
                        max_length=100,
                        verbose_name="Icono",
                    ),
                ),
                (
                    "icon_custom",
                    models.ImageField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to="dashboard/infoboxes/",
                        verbose_name="Icono personalizado para cuadro de informacion",
                    ),
                ),
                (
                    "color",
                    models.CharField(
                        default="#000000",
                        max_length=550,
                        verbose_name="Color de fondo del recuadro",
                    ),
                ),
                (
                    "size",
                    models.CharField(
                        blank=True,
                        choices=[("1", "Normal"), ("2", "Grande"), ("3", "Extra grande")],
                        default="1",
                        max_length=40,
                        null=True,
                        verbose_name="Tamano de recuadro",
                    ),
                ),
                (
                    "edge_style",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("1", "Izquierdo"),
                            ("2", "Derecho"),
                            ("3", "Superior"),
                            ("4", "Inferior"),
                            ("5", "Paralelos horizontales"),
                            ("6", "Paralelos verticales"),
                            ("7", "Borde completo"),
                            ("8", "Sin bordes"),
                        ],
                        default="8",
                        max_length=40,
                        null=True,
                        verbose_name="Tipo borde para recuadro",
                    ),
                ),
                (
                    "edge_color",
                    models.CharField(
                        blank=True,
                        default="#000000",
                        max_length=550,
                        null=True,
                        verbose_name="Color de borde del recuadro",
                    ),
                ),
                (
                    "text_color",
                    models.CharField(
                        default="#ffffff",
                        max_length=550,
                        verbose_name="Color de texto del recuadro",
                    ),
                ),
                ("stack_order", models.IntegerField(default=1)),
            ],
            options={
                "db_table": "sigic_dashboard_indicator_field_box_info",
                "ordering": ["stack_order"],
            },
        ),
        # --- SiteConfiguration ---
        migrations.CreateModel(
            name="SiteConfiguration",
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
                    "site",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configuration",
                        to="sigic_dashboard.site",
                    ),
                ),
                ("show_header", models.BooleanField(default=True, verbose_name="Mostrar encabezado")),
                ("show_footer", models.BooleanField(default=True, verbose_name="Mostrar pie de pagina")),
                (
                    "header_background_color",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        verbose_name="Color de fondo del encabezado",
                    ),
                ),
                (
                    "header_text_color",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        verbose_name="Color del texto del encabezado",
                    ),
                ),
                (
                    "header_font_size",
                    models.IntegerField(
                        blank=True,
                        default=28,
                        null=True,
                        verbose_name="Tamano de fuente del encabezado (px)",
                    ),
                ),
                (
                    "site_font_style",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("Roboto", "Roboto"),
                            ("Poppins", "Poppins"),
                            ("Nunito", "Nunito"),
                            ("Lato", "Lato"),
                            ("Aleo", "Aleo"),
                            ("Muli", "Muli"),
                            ("Arapey", "Arapey"),
                            ("Assistant", "Assistant"),
                            ("Barlow", "Barlow"),
                            ("Oswald", "Oswald"),
                            ("Bitter", "Bitter"),
                            ("Rokkitt", "Rokkitt"),
                            ("Carme", "Carme"),
                            ("Rubik", "Rubik"),
                            ("Gelasio", "Gelasio"),
                            ("Spectral", "Spectral"),
                            ("Alegreya", "Alegreya"),
                            ("Montserrat", "Montserrat"),
                            ("Abhaya Libre", "Abhaya Libre"),
                            ("Asap Condensed", "Asap Condensed"),
                            ("Source Sans Pro", "Source Sans Pro"),
                            ("Roboto Mono", "Roboto Mono"),
                            ("Merriweather Sans", "Merriweather Sans"),
                            ("Merriweather", "Merriweather"),
                            ("Architects Daughter", "Architects Daughter"),
                        ],
                        default="Roboto",
                        max_length=40,
                        null=True,
                        verbose_name="Tipo de letra del sitio",
                    ),
                ),
                (
                    "site_text_color",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        verbose_name="Color de texto del footer",
                    ),
                ),
                (
                    "site_interface_text_color",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        verbose_name="Color de texto de interfaz",
                    ),
                ),
                (
                    "site_background_color",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        verbose_name="Color de fondo del footer",
                    ),
                ),
                (
                    "site_interface_background_color",
                    models.CharField(
                        blank=True,
                        max_length=40,
                        null=True,
                        verbose_name="Color de fondo de los contenedores",
                    ),
                ),
                (
                    "site_font_size",
                    models.IntegerField(
                        blank=True,
                        default=16,
                        null=True,
                        verbose_name="Tamano de fuente del sitio (px)",
                    ),
                ),
                (
                    "indicator_box_title",
                    models.CharField(
                        blank=True,
                        default="Indicador",
                        max_length=255,
                        null=True,
                        verbose_name="Titulo del recuadro de seleccion de indicadores",
                    ),
                ),
            ],
            options={
                "db_table": "sigic_dashboard_site_configuration",
            },
        ),
    ]
