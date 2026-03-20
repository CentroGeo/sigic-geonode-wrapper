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
Modelos para la gestion de mapas interactivos.

Jerarquia: SigicMap -> MapLayer
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class MapType(models.TextChoices):
    REGULAR = "regular", "Regular"
    SWIPE = "swipe", "Swipe"
    DUAL = "dual", "Dual"


class MapPosition(models.TextChoices):
    LEFT = "left", "Izquierda"
    RIGHT = "right", "Derecha"


class SigicMapsBaseModel(models.Model):
    """fields common to all models."""

    updated_at = models.DateTimeField(
        verbose_name="created on", editable=False, auto_now=True
    )

    created_at = models.DateTimeField(
        verbose_name="modified on", editable=False, auto_now_add=True
    )

    class Meta:
        abstract = True

class SigicMap(SigicMapsBaseModel):
    """Contenedor principal del mapa con multiples capas."""

    name = models.CharField(
        verbose_name="Nombre del mapa",
        max_length=255
    )

    slug = models.SlugField(unique=True, max_length=30, blank=True)

    preview = models.ImageField(
        upload_to="sigic_mapas/previews/",
        null=True,
        blank=True,
        verbose_name="Previsualizacion del mapa"
    )

    zoom = models.IntegerField(
        verbose_name='zoom',
        default=5
    )

    center_lat = models.FloatField(
        verbose_name='center X',
        default=-101.61
    )

    center_long = models.FloatField(
        verbose_name='center Y',
        default=22.21
    )

    map_type = models.CharField(
        verbose_name="Tipo de mapa",
        max_length=20,
        choices=MapType.choices,
        default=MapType.REGULAR,
    )

    base_layer = models.CharField(
        max_length=255,
        verbose_name="Capa base",
        default="osm",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Propietario",
        on_delete=models.CASCADE
    )

    highlight_color = models.CharField(
        verbose_name="Color de resaltado",
        max_length=255,
        default="#ff51ba"
    )

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_slug = slugify(self.name)[:20]
            slug = base_slug
            suffix = 1

            while SigicMap.objects.filter(slug=slug).exists():
                # Adjust max length to leave room for suffix
                slug = f"{base_slug[:20 - len(str(suffix)) - 1]}-{suffix}"
                suffix += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = "sigic_map"
        verbose_name = "Mapa Sigic"
        verbose_name_plural = "Mapas Sigic"
        ordering = ["-updated_at"]



class MapLayer(SigicMapsBaseModel):
    """Capa de Geonode dentro de un mapa."""

    map = models.ForeignKey(
        SigicMap,
        on_delete=models.CASCADE,
        related_name="layers",
    )

    name = models.CharField(
        max_length=256,
        verbose_name='Nombre de la capa en Geoserver',
        blank=False
    )

    style = models.CharField(
        max_length=256,
        verbose_name='Estilo de la capa',
        blank=True
    )

    geonode_id = models.IntegerField(
        verbose_name='Id de la capa en Geonode',
        blank=True,
        null=True,
        db_index=True,
        help_text="ID de referencia de la capa en GeoNode",
    )

    map_position = models.CharField(
        verbose_name="Posición en el mapa (si aplica)",
        max_length=10,
        choices=MapPosition.choices,
        default=MapPosition.LEFT,
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

    def __str__(self):
        return f"Map: {self.map.name}, Layer: {self.name}"
    
    class Meta:
        db_table = "sigic_map_layers"
        verbose_name = "Capa de Mapa"
        verbose_name_plural = "Capas de Mapa"
        ordering = ["stack_order"]

    def save(self, *args, **kwargs):
        if self._state.adding:
            layers = MapLayer.objects.filter(map=self.map).order_by('-stack_order')
            if layers.exists():
                self.stack_order = layers[0].stack_order + 1
            else:
                self.stack_order = 1

        super().save(*args, **kwargs)