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


class HarvesterSimpleSerializer(serializers.ModelSerializer):
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

    url = serializers.URLField(
        required=True,
        help_text="URL del recurso remoto (archivo CSV, JSON, GeoJSON, XLS, XLSX)",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Descripción opcional del servicio",
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


class ServiceResponseSerializer(serializers.ModelSerializer):
    """Serializer para respuestas de Service con harvester_id."""

    url = serializers.URLField(source="base_url")
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


class ServiceDetailSerializer(ServiceResponseSerializer):
    """Serializer extendido con detalles del Harvester."""

    harvester = HarvesterSimpleSerializer(read_only=True)

    class Meta(ServiceResponseSerializer.Meta):
        fields = ServiceResponseSerializer.Meta.fields + ["harvester"]
