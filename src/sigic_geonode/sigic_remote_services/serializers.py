# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from rest_framework import serializers
from geonode.services.models import Service
from geonode.harvesting.models import Harvester


class HarvesterNestedSerializer(serializers.ModelSerializer):
    """Serializer reducido para mostrar información básica del Harvester."""

    class Meta:
        model = Harvester
        fields = [
            "id",
            "name",
            "status",
            "remote_available",
            "num_harvestable_resources",
            "last_updated",
        ]


class ServiceCreateSerializer(serializers.Serializer):
    """Serializer para crear un nuevo servicio remoto."""

    SERVICE_TYPE_CHOICES = [
        ("AUTO", "Detección automática"),
        ("OWS", "OGC Web Services"),
        ("WMS", "Web Map Service"),
        ("GN_WMS", "GeoNode Web Map Service"),
        ("REST_MAP", "ArcGIS REST MapServer"),
        ("REST_IMG", "ArcGIS REST ImageServer"),
        ("FILE", "Archivo (CSV, JSON, GeoJSON, XLS, XLSX)"),
    ]

    url = serializers.URLField(
        required=True,
        help_text="URL del servicio remoto (OWS, WMS, WFS, ArcGIS REST o archivo)",
    )
    type = serializers.ChoiceField(
        choices=SERVICE_TYPE_CHOICES,
        default="AUTO",
        required=False,
        help_text="Tipo de servicio. Si es AUTO, se detectará automáticamente.",
    )
    title = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Título del servicio. Si no se envía, se obtiene del servicio remoto.",
    )
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Nombre del servicio. Si no se envía, se genera de la URL.",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Descripción corta del servicio (máx 255 caracteres).",
    )
    abstract = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text="Descripción larga del servicio (máx 2000 caracteres).",
    )

    def validate_url(self, value):
        """Valida que la URL no exista ya para este usuario."""
        request = self.context.get("request")
        if request and request.user:
            exists = Service.objects.filter(
                base_url=value, owner=request.user
            ).exists()
            if exists:
                raise serializers.ValidationError(
                    "Ya existe un servicio con esta URL para tu usuario."
                )
        return value


class ServiceListSerializer(serializers.ModelSerializer):
    """Serializer para listado de servicios con campos básicos."""

    url = serializers.URLField(source="base_url", read_only=True)
    harvester_id = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "uuid",
            "url",
            "name",
            "title",
            "description",
            "abstract",
            "type",
            "harvester_id",
            "owner",
            "created",
        ]

    def get_harvester_id(self, obj):
        if obj.harvester:
            return obj.harvester.id
        return None

    def get_owner(self, obj):
        if obj.owner:
            return {"pk": obj.owner.pk, "username": obj.owner.username}
        return None


class ServiceDetailSerializer(ServiceListSerializer):
    """Serializer extendido con detalles del Harvester."""

    harvester = HarvesterNestedSerializer(read_only=True)

    class Meta(ServiceListSerializer.Meta):
        fields = ServiceListSerializer.Meta.fields + ["harvester"]
