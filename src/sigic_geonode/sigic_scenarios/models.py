# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este codigo fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene credito de autoria, pero la titularidad del codigo
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Modelos para la gestion de escenarios narrativos con mapas interactivos.

Jerarquia: Scenario -> Scene -> SceneLayer / SceneMarker
"""

from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------

class Scenario(models.Model):
    """Contenedor principal de un relato narrativo con multiples escenas."""

    name = models.CharField(
        max_length=256,
        verbose_name="Nombre",
        help_text="Nombre del escenario",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Propietario",
        on_delete=models.CASCADE,
        related_name="scenarios",
    )
    url_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="Publico",
        help_text="Si esta marcado, el escenario sera visible para todos los usuarios.",
    )
    card_image = models.ImageField(
        upload_to="scenarios/cards/",
        null=True,
        blank=True,
        verbose_name="Imagen de portada",
        help_text="Imagen que representa el escenario",
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripcion",
        help_text="Descripcion detallada del escenario",
    )
    scenes_layout_styles = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Estilos de layout",
        help_text="Configuracion del layout de las escenas",
    )

    class Meta:
        db_table = "sigic_scenarios"
        verbose_name = "Escenario"
        verbose_name_plural = "Escenarios"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

class SceneTextPosition(models.TextChoices):
    LEFT = "left", "Izquierda"
    RIGHT = "right", "Derecha"


def default_scene_styles():
    """Estilos por defecto para el panel de una escena."""
    return {
        "text_panel": 40,
        "map_panel": 60,
    }


class Scene(models.Model):
    """Escena individual dentro de un escenario; contiene mapa, texto, capas y marcadores."""

    name = models.CharField(
        max_length=256,
        verbose_name="Nombre",
        help_text="Nombre de la escena",
    )
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="scenes",
    )
    map_center_lat = models.FloatField(null=True, blank=True)
    map_center_long = models.FloatField(null=True, blank=True)
    zoom = models.IntegerField(null=True, blank=True)
    text_position = models.CharField(
        max_length=5,
        choices=SceneTextPosition.choices,
        default=SceneTextPosition.LEFT,
        verbose_name="Posicion del texto",
        help_text="Posicion del texto dentro de una escena",
    )
    text_content = models.TextField(
        blank=True,
        null=True,
        verbose_name="Contenido",
        help_text="Texto HTML de la escena",
    )
    styles = models.JSONField(
        verbose_name="Estilo de la escena",
        null=True,
        blank=True,
        default=default_scene_styles,
    )
    stack_order = models.IntegerField(default=0)

    class Meta:
        db_table = "sigic_scenes"
        verbose_name = "Escena"
        verbose_name_plural = "Escenas"
        ordering = ["stack_order"]

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        # Auto-incrementar stack_order al crear una nueva escena
        if self._state.adding:
            top = (
                Scene.objects.filter(scenario=self.scenario)
                .order_by("-stack_order")
                .first()
            )
            self.stack_order = (top.stack_order + 1) if top else 1
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# SceneLayer
# ---------------------------------------------------------------------------

class SceneLayer(models.Model):
    """Referencia a una capa WMS/GeoServer asociada a una escena."""

    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="layers",
    )
    geonode_id = models.IntegerField(
        verbose_name="ID de la capa en GeoNode",
        blank=True,
        null=True,
        db_index=True,
        help_text="ID de referencia de la capa en GeoNode",
    )
    name = models.CharField(
        max_length=256,
        verbose_name="Nombre de la capa (typename)",
        help_text="Nombre tecnico de la capa en GeoServer",
    )
    style = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        verbose_name="Nombre del estilo",
        help_text="Nombre del estilo aplicado a la capa",
    )
    style_title = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        verbose_name="Titulo del estilo",
        help_text="Titulo del estilo aplicado a la capa",
    )
    visible = models.BooleanField(
        default=True,
        verbose_name="Visible",
        help_text="Si la capa esta visible en el mapa",
    )
    opacity = models.FloatField(
        default=1.0,
        verbose_name="Opacidad",
        help_text="Opacidad de la capa (0.0 a 1.0)",
    )
    stack_order = models.IntegerField(
        default=0,
        verbose_name="Orden de apilamiento",
        help_text="Orden de las capas en el mapa (mayor = arriba)",
    )

    class Meta:
        db_table = "sigic_scene_layers"
        verbose_name = "Capa de escena"
        verbose_name_plural = "Capas de escena"
        ordering = ["stack_order"]

    def __str__(self):
        return f"{self.name} (Scene: {self.scene_id})"

    def save(self, *args, **kwargs):
        # Auto-incrementar stack_order al crear una nueva capa
        if self._state.adding:
            top = (
                SceneLayer.objects.filter(scene=self.scene)
                .order_by("-stack_order")
                .first()
            )
            self.stack_order = (top.stack_order + 1) if top else 1
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# SceneMarker
# ---------------------------------------------------------------------------

class SceneMarker(models.Model):
    """Marcador puntual sobre el mapa de una escena, con contenido emergente."""

    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="markers",
    )
    lat = models.DecimalField(
        max_digits=19,
        decimal_places=10,
        verbose_name="Latitud",
    )
    lng = models.DecimalField(
        max_digits=19,
        decimal_places=10,
        verbose_name="Longitud",
    )
    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Titulo",
    )
    content = models.TextField(
        null=True,
        blank=True,
        verbose_name="Contenido del marcador",
    )
    icon = models.CharField(
        max_length=50,
        default="fas fa-map-marker-alt",
        verbose_name="Icono",
        help_text="Clase de Font Awesome",
    )
    color = models.CharField(
        max_length=7,
        default="#ec4899",
        verbose_name="Color del marcador",
        help_text="Color hexadecimal",
    )
    image_url = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    options = models.JSONField(
        verbose_name="Opciones del marcador",
        null=True,
        blank=True,
        default=dict,
        help_text="Opciones adicionales en formato JSON",
    )

    class Meta:
        db_table = "sigic_scene_markers"
        verbose_name = "Marcador de escena"
        verbose_name_plural = "Marcadores de escena"
        ordering = ["id"]

    def __str__(self):
        return f"Marker {self.id} - {self.title or 'Sin titulo'}"
