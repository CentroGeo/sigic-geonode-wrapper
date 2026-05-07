# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Modelos para el sistema de indicadores geoespaciales (dashboard).

Jerarquía: Site → IndicatorGroup → SubGroup → Indicator → IndicatorFieldBoxInfo
           Site → SiteConfiguration (1:1)
           Site → SiteLogos (FK)
"""

from django.db import models


FONTS = (
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
)

SIZE = (
    ("1", "Normal"),
    ("2", "Grande"),
    ("3", "Extra grande"),
)

EDGE = (
    ("1", "Izquierdo"),
    ("2", "Derecho"),
    ("3", "Superior"),
    ("4", "Inferior"),
    ("5", "Paralelos horizontales"),
    ("6", "Paralelos verticales"),
    ("7", "Borde completo"),
    ("8", "Sin bordes"),
)


class Site(models.Model):

    name = models.CharField(
        verbose_name="Nombre del sitio",
        help_text="Nombre corto para identificar rapidamente el sitio",
        max_length=250,
        unique=True,
    )

    info_text = models.TextField(
        verbose_name="Informacion de sitio",
        help_text="Opcional",
        null=True,
        blank=True,
    )

    title = models.CharField(
        verbose_name="Titulo del sitio",
        max_length=500,
    )

    subtitle = models.CharField(
        verbose_name="Subtitulo del sitio",
        max_length=500,
    )

    url = models.CharField(
        verbose_name="URL del sitio",
        max_length=500,
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("dashboard-site-preview", kwargs={"site_id": self.pk})

    class Meta:
        db_table = "sigic_dashboard_site"
        ordering = ["name"]


class SiteLogos(models.Model):

    site = models.ForeignKey(
        Site,
        related_name="logos",
        on_delete=models.CASCADE,
    )

    icon = models.ImageField(
        verbose_name="Logo",
        upload_to="dashboard/logos/",
        blank=True,
        null=True,
        default=None,
    )

    icon_link = models.URLField(
        verbose_name="Link del logo",
        blank=True,
        default="",
    )

    stack_order = models.IntegerField(default=1)

    class Meta:
        db_table = "sigic_dashboard_site_logos"
        ordering = ["stack_order"]


class IndicatorGroup(models.Model):

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="groups",
    )

    name = models.CharField(
        verbose_name="Nombre del grupo de indicadores",
        max_length=250,
    )

    info_text = models.TextField(
        verbose_name="Informacion de grupo",
        help_text="Opcional",
        null=True,
        blank=True,
    )

    description = models.CharField(
        verbose_name="Descripcion del grupo",
        max_length=250,
    )

    stack_order = models.IntegerField(default=1)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sigic_dashboard_indicator_group"
        ordering = ["stack_order"]


class SubGroup(models.Model):

    group = models.ForeignKey(
        IndicatorGroup,
        on_delete=models.CASCADE,
        related_name="subgroups",
    )

    name = models.CharField(
        verbose_name="Nombre del subgrupo de indicadores",
        max_length=250,
    )

    info_text = models.TextField(
        verbose_name="Informacion de subgrupo",
        help_text="Opcional",
        null=True,
        blank=True,
    )

    icon = models.CharField(
        verbose_name="Icono del subgrupo",
        help_text="Clase CSS de Font Awesome (e.g. 'fas fa-chart-bar')",
        max_length=100,
        blank=True,
        default="",
    )

    icon_custom = models.ImageField(
        verbose_name="Icono personalizado del subgrupo",
        upload_to="dashboard/subgroups/",
        blank=True,
        null=True,
        default=None,
    )

    stack_order = models.IntegerField(default=1)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sigic_dashboard_subgroup"
        ordering = ["stack_order"]


class Indicator(models.Model):

    subgroup = models.ForeignKey(
        SubGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="indicators",
    )

    group = models.ForeignKey(
        IndicatorGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="indicators",
    )

    site = models.ForeignKey(
        Site,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="indicators",
    )

    name = models.CharField(
        verbose_name="Nombre del indicador",
        max_length=250,
    )

    plot_type = models.CharField(
        verbose_name="Tipo de grafica",
        max_length=250,
    )

    info_text = models.TextField(
        verbose_name="Informacion de indicador",
        help_text="Opcional",
        null=True,
        blank=True,
    )

    layer = models.ForeignKey(
        "layers.Dataset",
        verbose_name="Capa de indicador",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name="+",
    )

    layer_id_field = models.CharField(
        verbose_name="Campo id para identificar geometrias de la capa",
        max_length=550,
    )

    layer_nom_field = models.CharField(
        verbose_name="Campo para nombrar geometrias de la capa",
        max_length=550,
        blank=True,
        null=True,
    )

    high_values_percentage = models.IntegerField(
        verbose_name="Porcentaje de geometrias a recuperar",
        default=10,
        blank=True,
        null=True,
    )

    use_single_field = models.BooleanField(
        verbose_name="Generar grafica con un solo campo",
        default=False,
    )

    is_histogram = models.BooleanField(
        verbose_name="Indicador de histograma",
        default=False,
    )

    histogram_fields = models.JSONField(
        verbose_name="Campos para generar el histograma",
        blank=True,
        null=True,
    )

    field_one = models.CharField(
        verbose_name="Campo 1",
        max_length=550,
    )

    field_two = models.CharField(
        verbose_name="Campo 2",
        max_length=550,
        blank=True,
        null=True,
    )

    field_popup = models.JSONField(
        verbose_name="Campos para desplegar info en el popup",
        blank=True,
        null=True,
    )

    category_method = models.CharField(
        verbose_name="Metodo de clasificacion",
        max_length=250,
        blank=True,
        null=True,
    )

    field_category = models.IntegerField(
        verbose_name="Numero de categorias para grafica",
        blank=True,
        null=True,
        default=5,
    )

    colors = models.CharField(
        verbose_name="Colores de grafico y tematizacion",
        max_length=250,
        blank=True,
        null=True,
    )

    use_custom_colors = models.BooleanField(
        verbose_name="Usar colores provistos por el cliente",
        default=False,
    )

    custom_colors = models.CharField(
        verbose_name="Colores custom de grafico y tematizacion",
        max_length=250,
        blank=True,
        null=True,
    )

    plot_config = models.JSONField(
        verbose_name="Configuracion para la grafica",
        blank=True,
        null=True,
    )

    plot_values = models.JSONField(
        verbose_name="Valores para la grafica",
        blank=True,
        null=True,
    )

    map_values = models.JSONField(
        verbose_name="Valores para tematizacion de la capa",
        blank=True,
        null=True,
    )

    show_general_values = models.BooleanField(
        verbose_name="Mostrar valores generales",
        default=False,
    )

    general_values = models.JSONField(
        verbose_name="Valores generales agregados para cuadros KPI",
        blank=True,
        null=True,
    )

    use_filter = models.BooleanField(
        verbose_name="Activar filtro",
        default=False,
    )

    filters = models.JSONField(
        verbose_name="Filtros",
        blank=True,
        null=True,
    )

    stack_order = models.IntegerField(default=1)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sigic_dashboard_indicator"
        ordering = ["stack_order"]


class IndicatorFieldBoxInfo(models.Model):

    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        related_name="infoboxes",
    )

    field = models.CharField(
        verbose_name="Campo de informacion",
        max_length=550,
    )

    is_percentage = models.BooleanField(
        verbose_name="Es de porcentaje?",
        default=False,
    )

    field_percentage_total = models.CharField(
        verbose_name="Campo total para calcular porcentaje",
        max_length=550,
        blank=True,
        null=True,
    )

    name = models.CharField(
        verbose_name="Nombre del campo",
        max_length=550,
    )

    icon = models.CharField(
        verbose_name="Icono",
        help_text="Clase CSS de Font Awesome (e.g. 'fas fa-chart-bar')",
        max_length=100,
        blank=True,
        default="",
    )

    icon_custom = models.ImageField(
        verbose_name="Icono personalizado para cuadro de informacion",
        upload_to="dashboard/infoboxes/",
        blank=True,
        null=True,
        default=None,
    )

    color = models.CharField(
        verbose_name="Color de fondo del recuadro",
        max_length=550,
        default="#000000",
    )

    size = models.CharField(
        verbose_name="Tamano de recuadro",
        max_length=40,
        choices=SIZE,
        blank=True,
        null=True,
        default="1",
    )

    edge_style = models.CharField(
        verbose_name="Tipo borde para recuadro",
        max_length=40,
        choices=EDGE,
        blank=True,
        null=True,
        default="8",
    )

    edge_color = models.CharField(
        verbose_name="Color de borde del recuadro",
        max_length=550,
        default="#000000",
        blank=True,
        null=True,
    )

    text_color = models.CharField(
        verbose_name="Color de texto del recuadro",
        max_length=550,
        default="#ffffff",
    )

    stack_order = models.IntegerField(default=1)

    class Meta:
        db_table = "sigic_dashboard_indicator_field_box_info"
        ordering = ["stack_order"]


class SiteConfiguration(models.Model):

    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name="configuration",
    )

    show_header = models.BooleanField(default=True, verbose_name="Mostrar encabezado")
    show_footer = models.BooleanField(default=True, verbose_name="Mostrar pie de pagina")

    header_background_color = models.CharField(
        verbose_name="Color de fondo del encabezado",
        max_length=40,
        blank=True,
        null=True,
    )

    header_text_color = models.CharField(
        verbose_name="Color del texto del encabezado",
        max_length=40,
        blank=True,
        null=True,
    )

    header_font_size = models.IntegerField(
        verbose_name="Tamano de fuente del encabezado (px)",
        blank=True,
        null=True,
        default=28,
    )

    site_font_style = models.CharField(
        verbose_name="Tipo de letra del sitio",
        max_length=40,
        choices=FONTS,
        blank=True,
        null=True,
        default="Roboto",
    )

    site_text_color = models.CharField(
        verbose_name="Color de texto del footer",
        max_length=40,
        blank=True,
        null=True,
    )

    site_interface_text_color = models.CharField(
        verbose_name="Color de texto de interfaz",
        max_length=40,
        blank=True,
        null=True,
    )

    site_background_color = models.CharField(
        verbose_name="Color de fondo del footer",
        max_length=40,
        blank=True,
        null=True,
    )

    site_interface_background_color = models.CharField(
        verbose_name="Color de fondo de los contenedores",
        max_length=40,
        blank=True,
        null=True,
    )

    site_font_size = models.IntegerField(
        verbose_name="Tamano de fuente del sitio (px)",
        blank=True,
        null=True,
        default=16,
    )

    indicator_box_title = models.CharField(
        verbose_name="Titulo del recuadro de seleccion de indicadores",
        default="Indicador",
        max_length=255,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "sigic_dashboard_site_configuration"
