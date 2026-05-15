# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from rest_framework import serializers

from .models import DataImportJob


class DataImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImportJob
        fields = [
            "id", "status", "error_message",
            "original_filename", "file_format",
            "column_schema",
            "geo_strategy", "geo_field_lat", "geo_field_lon", "geo_field_join",
            "geonode_dataset_id", "dashboard_site_id",
            "layer_abstract", "layer_keywords", "layer_license",
            "layer_category", "layer_attribution", "style_specs",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "error_message",
            "file_format", "original_filename",
            "geonode_dataset_id", "dashboard_site_id",
            "created_at", "updated_at",
        ]


class SchemaUpdateSerializer(serializers.Serializer):
    """Permite al usuario corregir tipos de columnas y estrategia geo."""
    column_schema = serializers.ListField(child=serializers.DictField(), required=False)
    geo_strategy = serializers.ChoiceField(
        choices=[c[0] for c in DataImportJob.GEO_STRATEGIES],
        required=False,
    )
    geo_field_lat = serializers.CharField(required=False, allow_blank=True)
    geo_field_lon = serializers.CharField(required=False, allow_blank=True)
    geo_field_join = serializers.CharField(required=False, allow_blank=True)


class GeoPreviewSerializer(serializers.Serializer):
    geo_strategy = serializers.ChoiceField(choices=[c[0] for c in DataImportJob.GEO_STRATEGIES])
    geo_field_lat = serializers.CharField(required=False, allow_blank=True, default="")
    geo_field_lon = serializers.CharField(required=False, allow_blank=True, default="")
    geo_field_join = serializers.CharField(required=False, allow_blank=True, default="")


class CreateTableroSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=250)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    layer_abstract = serializers.CharField(required=False, allow_blank=True, default="")
    layer_keywords = serializers.CharField(required=False, allow_blank=True, default="")
    layer_license = serializers.CharField(required=False, allow_blank=True, default="")
    layer_category = serializers.CharField(required=False, allow_blank=True, default="")
    layer_attribution = serializers.CharField(required=False, allow_blank=True, default="")
    style_specs = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )
