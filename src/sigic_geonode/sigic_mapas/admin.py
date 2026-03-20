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
Registro de modelos de mapas en el admin de Django.
"""

from django.contrib import admin

from .models import SigicMap, MapLayer

class MapLayerInline(admin.TabularInline):
    """Capas anidadas dentro del admin del mapa."""
    model = MapLayer
    extra = 0
    fields = ("name", "style", "map_position", "visible", "opacity", "geonode_id", "stack_order")
    readonly_fields = ("stack_order",)
    ordering = ("stack_order",)


@admin.register(SigicMap)
class SigicMapAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "owner__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = [MapLayerInline]

@admin.register(MapLayer)
class MapLayerAdmin(admin.ModelAdmin):
    list_display = ("name", "map", "geonode_id", "visible", "opacity", "stack_order")
    list_filter = ("visible",)
    search_fields = ("name",)
    readonly_fields = ("stack_order","created_at", "updated_at")