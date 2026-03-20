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
Serializers DRF para los modelos de maps y maplayers.
"""

from geonode.layers.models import Dataset
from rest_framework import serializers

from .models import SigicMap, MapLayer


class SigicMapListSerializer(serializers.ModelSerializer):
    """Serializer para listado de mapas con resumen basico."""

    owner = serializers.SerializerMethodField()
    layers_count = serializers.SerializerMethodField()

    class Meta:
        model = SigicMap
        fields = [
            "id",
            "name",
            "owner",
            "slug",
            "preview",
            "layers_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "owner", "layers_count"]

    def get_owner(self, obj):
        return {"pk": obj.owner.pk, "username": obj.owner.username}

    def get_layers_count(self, obj):
        return obj.layers.count()

class MapLayerBasicSerializer(serializers.ModelSerializer):
    """Serializer reducido de capas para anidar dentro de SigicMapDetail."""

    class Meta:
        model = MapLayer
        fields = ["id", "name", "style", "stack_order"]

class SigicMapDetailSerializer(SigicMapListSerializer):
    """Serializer extendido con lista basica de capas."""

    layers = serializers.SerializerMethodField()

    class Meta(SigicMapListSerializer.Meta):
        fields = SigicMapListSerializer.Meta.fields + ["layers"]

    def get_layers(self, obj):
        layers = obj.layers.order_by("stack_order")
        return MapLayerBasicSerializer(layers, many=True).data


class SigicMapCreateSerializer(serializers.ModelSerializer):
    """Serializer para creacion de mapas."""

    class Meta:
        model = SigicMap
        fields = [
            "id",
            "name",
            "slug",
            "map_type",
            "highlight_color",
        ]
        read_only_fields = ["id"]

class SigicMapUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizacion parcial de mapas."""

    class Meta:
        model = SigicMap
        fields = [
            "name",
            "slug",
            "preview",
            "zoom",
            "center_lat",
            "center_long",
            "map_type",
            "base_layer",
            "highlight_color",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "slug": {"required": False},
            "zoom": {"required": False},
            "center_lat": {"required": False},
            "center_long": {"required": False},
            "map_type": {"required": False},
            "base_layer": {"required": False},
            "highlight_color": {"required": False},
        }

class MapLayerSerializer(serializers.ModelSerializer):
    """Serializer de lectura para capas de mapa."""

    dataset_title = serializers.SerializerMethodField()

    class Meta:
        model = MapLayer
        fields = [
            "id",
            "map",
            "name",
            "style",
            "geonode_id",
            "map_position",
            "visible",
            "opacity",
            "stack_order",
        ]
        read_only_fields = ["id", "stack_order"]

    def get_dataset_title(self, obj):
        """Retorna el titulo del Dataset vinculado en GeoNode, si existe."""
        if obj.geonode_id is None:
            return None
        try:
            return Dataset.objects.values_list("title", flat=True).get(pk=obj.geonode_id)
        except Dataset.DoesNotExist:
            return None

class MapLayerCreateSerializer(serializers.ModelSerializer):
    """Serializer para creacion de capas.

    Valida que geonode_id corresponda a un Dataset existente de tipo capa
    y auto-rellena el campo name con el alternate del Dataset.
    """

    class Meta:
        model = MapLayer
        fields = [
            "map",
            "geonode_id",
            "name",
            "style",
            "visible",
            "opacity",
            "map_position",
        ]
        extra_kwargs = {
            "geonode_id": {"required": True},
            "name": {"required": False},
            "map_position": {"required": False},
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

class MapLayerUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizacion parcial de capas."""

    class Meta:
        model = MapLayer
        fields = [
            "name",
            "geonode_id",
            "visible",
            "opacity",
            "map_position",
            "stack_order",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "geonode_id": {"required": False},
            "map_position": {"required": False},
            "visible": {"required": False},
            "opacity": {"required": False},
            "stack_order": {"required": False},
        }

class MapLayerStyleUpdateSerializer(serializers.Serializer):
    """Serializer exclusivo para actualizar estilo de una capa."""

    style = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class MapLayerReorderSerializer(serializers.Serializer):
    """Serializer para reordenamiento de capas en bloque."""

    id = serializers.IntegerField()
    stack_order = serializers.IntegerField()


class BulkIdSerializer(serializers.Serializer):
    """Serializer generico para operaciones bulk con IDs."""

    id = serializers.IntegerField()