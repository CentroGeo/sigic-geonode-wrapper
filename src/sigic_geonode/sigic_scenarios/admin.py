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
Registro de modelos de escenarios en el admin de Django.
"""

from django.contrib import admin

from .models import Scenario, Scene, SceneLayer, SceneMarker


class SceneInline(admin.TabularInline):
    """Escenas anidadas dentro del admin de Scenario."""
    model = Scene
    extra = 0
    fields = ("name", "stack_order", "text_position", "map_center_lat", "map_center_long", "zoom")
    readonly_fields = ("stack_order",)
    ordering = ("stack_order",)


class SceneLayerInline(admin.TabularInline):
    """Capas anidadas dentro del admin de Scene."""
    model = SceneLayer
    extra = 0
    fields = ("name", "geonode_id", "style", "visible", "opacity", "stack_order")
    readonly_fields = ("stack_order",)
    ordering = ("stack_order",)


class SceneMarkerInline(admin.TabularInline):
    """Marcadores anidados dentro del admin de Scene."""
    model = SceneMarker
    extra = 0
    fields = ("title", "lat", "lng", "icon", "color")


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_public", "created_at")
    list_filter = ("is_public", "created_at")
    search_fields = ("name", "description", "owner__username")
    readonly_fields = ("created_at",)
    inlines = [SceneInline]


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ("name", "scenario", "stack_order", "text_position")
    list_filter = ("text_position",)
    search_fields = ("name", "scenario__name")
    readonly_fields = ("stack_order",)
    inlines = [SceneLayerInline, SceneMarkerInline]


@admin.register(SceneLayer)
class SceneLayerAdmin(admin.ModelAdmin):
    list_display = ("name", "scene", "geonode_id", "visible", "opacity", "stack_order")
    list_filter = ("visible",)
    search_fields = ("name",)
    readonly_fields = ("stack_order",)


@admin.register(SceneMarker)
class SceneMarkerAdmin(admin.ModelAdmin):
    list_display = ("title", "scene", "lat", "lng", "icon", "color")
    search_fields = ("title",)
