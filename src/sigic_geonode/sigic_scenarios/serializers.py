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
Serializers DRF para los modelos de escenarios, escenas, capas y marcadores.
"""

from geonode.layers.models import Dataset
from rest_framework import serializers

from .models import Scenario, Scene, SceneLayer, SceneMarker


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------

class ScenarioListSerializer(serializers.ModelSerializer):
    """Serializer para listado de escenarios con resumen basico."""

    owner = serializers.SerializerMethodField()
    scene_count = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            "id",
            "name",
            "created_at",
            "owner",
            "url_id",
            "is_public",
            "card_image",
            "description",
            "scenes_layout_styles",
            "scene_count",
        ]
        read_only_fields = ["id", "created_at", "owner", "scene_count"]

    def get_owner(self, obj):
        return {"pk": obj.owner.pk, "username": obj.owner.username}

    def get_scene_count(self, obj):
        return obj.scenes.count()


class SceneBasicSerializer(serializers.ModelSerializer):
    """Serializer reducido de escena para anidar dentro de ScenarioDetail."""

    class Meta:
        model = Scene
        fields = ["id", "name", "stack_order"]


class ScenarioDetailSerializer(ScenarioListSerializer):
    """Serializer extendido con lista basica de escenas anidadas."""

    scenes = serializers.SerializerMethodField()

    class Meta(ScenarioListSerializer.Meta):
        fields = ScenarioListSerializer.Meta.fields + ["scenes"]

    def get_scenes(self, obj):
        scenes = obj.scenes.order_by("stack_order")
        return SceneBasicSerializer(scenes, many=True).data


class ScenarioCreateSerializer(serializers.ModelSerializer):
    """Serializer para creacion de escenarios."""

    class Meta:
        model = Scenario
        fields = [
            "name",
            "url_id",
            "is_public",
            "description",
            "scenes_layout_styles",
        ]


class ScenarioUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizacion parcial de escenarios."""

    class Meta:
        model = Scenario
        fields = [
            "name",
            "url_id",
            "is_public",
            "description",
            "scenes_layout_styles",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "url_id": {"required": False},
            "is_public": {"required": False},
            "description": {"required": False},
            "scenes_layout_styles": {"required": False},
        }


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

class SceneSerializer(serializers.ModelSerializer):
    """Serializer completo de escena con capas y marcadores anidados."""

    layers = serializers.SerializerMethodField()
    markers = serializers.SerializerMethodField()

    class Meta:
        model = Scene
        fields = [
            "id",
            "name",
            "scenario",
            "map_center_lat",
            "map_center_long",
            "zoom",
            "text_position",
            "text_content",
            "styles",
            "stack_order",
            "layers",
            "markers",
        ]
        read_only_fields = ["id", "stack_order", "layers", "markers"]

    def get_layers(self, obj):
        return SceneLayerSerializer(
            obj.layers.order_by("stack_order"), many=True
        ).data

    def get_markers(self, obj):
        return SceneMarkerSerializer(obj.markers.all(), many=True).data


class SceneCreateSerializer(serializers.ModelSerializer):
    """Serializer para creacion de escenas."""

    class Meta:
        model = Scene
        fields = [
            "name",
            "scenario",
            "map_center_lat",
            "map_center_long",
            "zoom",
            "text_position",
            "text_content",
            "styles",
        ]


class SceneUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizacion parcial de escenas."""

    class Meta:
        model = Scene
        fields = [
            "name",
            "map_center_lat",
            "map_center_long",
            "zoom",
            "text_position",
            "text_content",
            "styles",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "map_center_lat": {"required": False},
            "map_center_long": {"required": False},
            "zoom": {"required": False},
            "text_position": {"required": False},
            "text_content": {"required": False},
            "styles": {"required": False},
        }


class SceneReorderSerializer(serializers.Serializer):
    """Serializer para reordenamiento de escenas en bloque."""

    id = serializers.IntegerField()
    stack_order = serializers.IntegerField()


# ---------------------------------------------------------------------------
# SceneLayer
# ---------------------------------------------------------------------------

class SceneLayerSerializer(serializers.ModelSerializer):
    """Serializer de lectura para capas de escena."""

    dataset_title = serializers.SerializerMethodField()

    class Meta:
        model = SceneLayer
        fields = [
            "id",
            "scene",
            "geonode_id",
            "name",
            "dataset_title",
            "style",
            "style_title",
            "visible",
            "opacity",
            "stack_order",
        ]
        read_only_fields = ["id", "stack_order", "dataset_title"]

    def get_dataset_title(self, obj):
        """Retorna el titulo del Dataset vinculado en GeoNode, si existe."""
        if obj.geonode_id is None:
            return None
        try:
            return Dataset.objects.values_list("title", flat=True).get(pk=obj.geonode_id)
        except Dataset.DoesNotExist:
            return None


class SceneLayerCreateSerializer(serializers.ModelSerializer):
    """Serializer para creacion de capas.

    Valida que geonode_id corresponda a un Dataset existente de tipo capa
    y auto-rellena el campo name con el alternate del Dataset.
    """

    class Meta:
        model = SceneLayer
        fields = [
            "scene",
            "geonode_id",
            "name",
            "style",
            "style_title",
            "visible",
            "opacity",
        ]
        extra_kwargs = {
            "geonode_id": {"required": True},
            "name": {"required": False},
        }

    def validate_geonode_id(self, value):
        """Verifica que exista un Dataset con este ID y que sea de tipo capa."""
        try:
            dataset = Dataset.objects.get(pk=value)
        except Dataset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un dataset en GeoNode con id {value}."
            )
        if dataset.subtype not in ("vector", "raster"):
            raise serializers.ValidationError(
                f"El dataset {value} no es de tipo capa "
                f"(subtype actual: {dataset.subtype})."
            )
        # Almacenar referencia para usar en validate()
        self._dataset = dataset
        return value

    def validate(self, attrs):
        # Auto-rellenar name con el alternate del Dataset si no se proporciono
        dataset = getattr(self, "_dataset", None)
        if dataset and not attrs.get("name"):
            attrs["name"] = dataset.alternate
        return attrs


class SceneLayerUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizacion parcial de capas."""

    class Meta:
        model = SceneLayer
        fields = [
            "name",
            "geonode_id",
            "visible",
            "opacity",
            "stack_order",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "geonode_id": {"required": False},
            "visible": {"required": False},
            "opacity": {"required": False},
            "stack_order": {"required": False},
        }


class SceneLayerStyleUpdateSerializer(serializers.Serializer):
    """Serializer exclusivo para actualizar estilo de una capa."""

    style = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    style_title = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class SceneLayerReorderSerializer(serializers.Serializer):
    """Serializer para reordenamiento de capas en bloque."""

    id = serializers.IntegerField()
    stack_order = serializers.IntegerField()


# ---------------------------------------------------------------------------
# SceneMarker
# ---------------------------------------------------------------------------

class SceneMarkerSerializer(serializers.ModelSerializer):
    """Serializer de lectura para marcadores de escena."""

    class Meta:
        model = SceneMarker
        fields = [
            "id",
            "scene",
            "lat",
            "lng",
            "title",
            "content",
            "icon",
            "color",
            "image_url",
            "options",
        ]
        read_only_fields = ["id"]


class SceneMarkerCreateSerializer(serializers.ModelSerializer):
    """Serializer para creacion de marcadores."""

    class Meta:
        model = SceneMarker
        fields = [
            "scene",
            "lat",
            "lng",
            "title",
            "content",
            "icon",
            "color",
            "image_url",
            "options",
        ]


class SceneMarkerUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizacion parcial de marcadores."""

    class Meta:
        model = SceneMarker
        fields = [
            "lat",
            "lng",
            "title",
            "content",
            "icon",
            "color",
            "image_url",
            "options",
        ]
        extra_kwargs = {
            "lat": {"required": False},
            "lng": {"required": False},
            "title": {"required": False},
            "content": {"required": False},
            "icon": {"required": False},
            "color": {"required": False},
            "image_url": {"required": False},
            "options": {"required": False},
        }


# ---------------------------------------------------------------------------
# Comun
# ---------------------------------------------------------------------------

class BulkIdSerializer(serializers.Serializer):
    """Serializer generico para operaciones bulk con IDs."""

    id = serializers.IntegerField()
