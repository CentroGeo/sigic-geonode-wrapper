# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Serializers DRF para los modelos del dashboard de indicadores.
"""

from rest_framework import serializers

from .models import (
    Indicator,
    IndicatorFieldBoxInfo,
    IndicatorGroup,
    Site,
    SiteConfiguration,
    SiteLogos,
    SubGroup,
)


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------

class SiteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "name", "title", "subtitle", "url"]
        read_only_fields = ["id"]


class SiteDetailSerializer(SiteListSerializer):
    logos = serializers.SerializerMethodField()
    configuration = serializers.SerializerMethodField()

    class Meta(SiteListSerializer.Meta):
        fields = SiteListSerializer.Meta.fields + ["info_text", "logos", "configuration"]

    def get_logos(self, obj):
        return SiteLogosSerializer(obj.logos.order_by("stack_order"), many=True).data

    def get_configuration(self, obj):
        try:
            return SiteConfigurationSerializer(obj.configuration).data
        except SiteConfiguration.DoesNotExist:
            return None


class SiteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "name", "title", "subtitle", "url", "info_text"]
        read_only_fields = ["id"]


class SiteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["name", "title", "subtitle", "url", "info_text"]
        extra_kwargs = {
            "name": {"required": False},
            "title": {"required": False},
            "subtitle": {"required": False},
            "url": {"required": False},
            "info_text": {"required": False},
        }


# ---------------------------------------------------------------------------
# SiteLogos
# ---------------------------------------------------------------------------

class SiteLogosSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteLogos
        fields = ["id", "site", "icon", "icon_link", "stack_order"]
        read_only_fields = ["id"]


class SiteLogosCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteLogos
        fields = ["site", "icon", "icon_link"]


# ---------------------------------------------------------------------------
# IndicatorGroup
# ---------------------------------------------------------------------------

class IndicatorGroupListSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorGroup
        fields = ["id", "site", "name", "description", "stack_order"]
        read_only_fields = ["id"]


class IndicatorGroupDetailSerializer(IndicatorGroupListSerializer):
    class Meta(IndicatorGroupListSerializer.Meta):
        fields = IndicatorGroupListSerializer.Meta.fields + ["info_text"]


class IndicatorGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorGroup
        fields = ["id", "site", "name", "info_text", "description", "stack_order"]
        read_only_fields = ["id"]


class IndicatorGroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorGroup
        fields = ["name", "info_text", "description", "stack_order"]
        extra_kwargs = {
            "name": {"required": False},
            "info_text": {"required": False},
            "description": {"required": False},
            "stack_order": {"required": False},
        }


# ---------------------------------------------------------------------------
# SubGroup
# ---------------------------------------------------------------------------

class SubGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubGroup
        fields = [
            "id", "group", "name", "info_text", "icon", "icon_custom", "stack_order",
        ]
        read_only_fields = ["id"]


class SubGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubGroup
        fields = ["group", "name", "info_text", "icon", "icon_custom"]


class SubGroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubGroup
        fields = ["name", "info_text", "icon", "icon_custom", "stack_order"]
        extra_kwargs = {
            "name": {"required": False},
            "info_text": {"required": False},
            "icon": {"required": False},
            "icon_custom": {"required": False},
            "stack_order": {"required": False},
        }


# ---------------------------------------------------------------------------
# IndicatorFieldBoxInfo
# ---------------------------------------------------------------------------

class IndicatorFieldBoxInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorFieldBoxInfo
        fields = [
            "id",
            "indicator",
            "field",
            "is_percentage",
            "field_percentage_total",
            "name",
            "icon",
            "icon_custom",
            "color",
            "size",
            "edge_style",
            "edge_color",
            "text_color",
            "stack_order",
        ]
        read_only_fields = ["id"]


class IndicatorFieldBoxInfoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorFieldBoxInfo
        fields = [
            "indicator",
            "field",
            "is_percentage",
            "field_percentage_total",
            "name",
            "icon",
            "icon_custom",
            "color",
            "size",
            "edge_style",
            "edge_color",
            "text_color",
            "stack_order",
        ]


# ---------------------------------------------------------------------------
# Indicator
# ---------------------------------------------------------------------------

class IndicatorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = [
            "id",
            "site",
            "group",
            "subgroup",
            "layer",
            "name",
            "plot_type",
            "is_histogram",
            "stack_order",
        ]
        read_only_fields = ["id"]


class IndicatorDetailSerializer(IndicatorListSerializer):
    infoboxes = serializers.SerializerMethodField()

    class Meta(IndicatorListSerializer.Meta):
        fields = IndicatorListSerializer.Meta.fields + [
            "info_text",
            "layer_id_field",
            "layer_nom_field",
            "high_values_percentage",
            "use_single_field",
            "histogram_fields",
            "field_one",
            "field_two",
            "field_popup",
            "category_method",
            "field_category",
            "colors",
            "use_custom_colors",
            "custom_colors",
            "plot_config",
            "plot_values",
            "map_values",
            "show_general_values",
            "use_filter",
            "filters",
            "infoboxes",
        ]

    def get_infoboxes(self, obj):
        return IndicatorFieldBoxInfoSerializer(
            obj.infoboxes.order_by("stack_order"), many=True
        ).data


class IndicatorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = [
            "id",
            "site",
            "group",
            "subgroup",
            "layer",
            "name",
            "plot_type",
            "info_text",
            "layer_id_field",
            "layer_nom_field",
            "high_values_percentage",
            "use_single_field",
            "is_histogram",
            "histogram_fields",
            "field_one",
            "field_two",
            "field_popup",
            "category_method",
            "field_category",
            "colors",
            "use_custom_colors",
            "custom_colors",
            "plot_config",
            "plot_values",
            "map_values",
            "show_general_values",
            "use_filter",
            "filters",
            "stack_order",
        ]
        read_only_fields = ["id"]


class IndicatorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = [
            "site",
            "group",
            "subgroup",
            "layer",
            "name",
            "plot_type",
            "info_text",
            "layer_id_field",
            "layer_nom_field",
            "high_values_percentage",
            "use_single_field",
            "is_histogram",
            "histogram_fields",
            "field_one",
            "field_two",
            "field_popup",
            "category_method",
            "field_category",
            "colors",
            "use_custom_colors",
            "custom_colors",
            "plot_config",
            "plot_values",
            "map_values",
            "show_general_values",
            "use_filter",
            "filters",
            "stack_order",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


class IndicatorBuildDataSerializer(serializers.Serializer):
    """Input para la accion build-data."""

    field_id = serializers.CharField()
    field_one = serializers.CharField()
    field_two = serializers.CharField(required=False, allow_blank=True, default="")
    method = serializers.CharField()
    categories = serializers.IntegerField(default=5)
    manual_bins = serializers.CharField(required=False, allow_blank=True, default="")


class IndicatorSaveDataSerializer(serializers.Serializer):
    """Input para la accion save-data (adapta ambos casos: regular e histograma)."""

    field_id = serializers.CharField(required=False, default="")
    single_field = serializers.BooleanField(required=False, default=False)
    field_one = serializers.CharField(required=False, allow_blank=True, default="")
    field_two = serializers.CharField(required=False, allow_blank=True, default="")
    field_name = serializers.CharField(required=False, allow_blank=True, default="")
    field_popup = serializers.JSONField(required=False, allow_null=True)
    category_method = serializers.CharField(required=False, allow_blank=True, default="")
    field_category = serializers.IntegerField(required=False, default=5)
    colors = serializers.CharField(required=False, allow_blank=True, default="")
    use_custom_color = serializers.BooleanField(required=False, default=False)
    custom_colors = serializers.CharField(required=False, allow_blank=True, default="")
    plot_values = serializers.JSONField(required=False, allow_null=True)
    map_values = serializers.JSONField(required=False, allow_null=True)
    plot_config = serializers.JSONField(required=False, allow_null=True)
    use_filter = serializers.BooleanField(required=False, default=False)
    filters = serializers.JSONField(required=False, allow_null=True)
    high_values = serializers.IntegerField(required=False, default=10)
    histogram_fields = serializers.JSONField(required=False, allow_null=True)
    general_values = serializers.BooleanField(required=False, default=False)


class IndicatorCloneSerializer(serializers.Serializer):
    """Input para la accion clone."""

    field_one = serializers.CharField()
    field_two = serializers.CharField(required=False, allow_blank=True, default="")
    name = serializers.CharField(required=False, allow_blank=True, default="")
    clone_boxes = serializers.BooleanField(required=False, default=False)


# ---------------------------------------------------------------------------
# SiteConfiguration
# ---------------------------------------------------------------------------

class SiteConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfiguration
        fields = [
            "id",
            "site",
            "show_header",
            "show_footer",
            "header_background_color",
            "header_text_color",
            "header_font_size",
            "site_font_style",
            "site_text_color",
            "site_interface_text_color",
            "site_background_color",
            "site_interface_background_color",
            "site_font_size",
            "indicator_box_title",
        ]
        read_only_fields = ["id", "site"]


# ---------------------------------------------------------------------------
# Comun
# ---------------------------------------------------------------------------

class BulkIdSerializer(serializers.Serializer):
    """Serializer generico para operaciones bulk con IDs."""

    id = serializers.IntegerField()


class ReorderSerializer(serializers.Serializer):
    """Serializer para reordenamiento en bloque."""

    id = serializers.IntegerField()
    stack_order = serializers.IntegerField()
