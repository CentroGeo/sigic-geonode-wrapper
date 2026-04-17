# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
ViewSets para el dashboard de indicadores geoespaciales.

Expone una API REST completa para Sites, Logos, Grupos, Subgrupos,
Indicadores, InfoBoxes y Configuracion de sitio.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

from .models import (
    Indicator,
    IndicatorFieldBoxInfo,
    IndicatorGroup,
    Site,
    SiteConfiguration,
    SiteLogos,
    SubGroup,
)
from .permissions import IsDashboardAdmin
from .serializers import (
    BulkIdSerializer,
    IndicatorBuildDataSerializer,
    IndicatorCloneSerializer,
    IndicatorCreateSerializer,
    IndicatorDetailSerializer,
    IndicatorFieldBoxInfoCreateSerializer,
    IndicatorFieldBoxInfoSerializer,
    IndicatorGroupCreateSerializer,
    IndicatorGroupDetailSerializer,
    IndicatorGroupListSerializer,
    IndicatorGroupUpdateSerializer,
    IndicatorListSerializer,
    IndicatorSaveDataSerializer,
    IndicatorUpdateSerializer,
    ReorderSerializer,
    SiteConfigurationSerializer,
    SiteCreateSerializer,
    SiteDetailSerializer,
    SiteListSerializer,
    SiteLogosCreateSerializer,
    SiteLogosSerializer,
    SiteUpdateSerializer,
    SubGroupCreateSerializer,
    SubGroupSerializer,
    SubGroupUpdateSerializer,
)
from .utils.indicator_utils import assign_color, get_data_from_db, process_data

logger = logging.getLogger(__name__)


class DashboardPagination(PageNumberPagination):
    """Paginacion compatible con la estructura de respuesta de GeoNode."""

    page_size = 10
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return Response(
            {
                "links": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "total": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "results": data,
            }
        )


AUTHENTICATION_CLASSES = [
    BasicAuthentication,
    SessionAuthentication,
    OAuth2Authentication,
    KeycloakJWTAuthentication,
]


# ---------------------------------------------------------------------------
# SiteViewSet
# ---------------------------------------------------------------------------

class SiteViewSet(ModelViewSet):
    """ViewSet para gestionar sitios del dashboard."""

    authentication_classes = AUTHENTICATION_CLASSES
    pagination_class = DashboardPagination
    queryset = Site.objects.all().order_by("name")

    def get_permissions(self):
        if self.action in ("list", "retrieve", "logos"):
            return [permissions.AllowAny()]
        if self.action == "config" and self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsDashboardAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return SiteCreateSerializer
        if self.action in ("update", "partial_update"):
            return SiteUpdateSerializer
        if self.action == "retrieve":
            return SiteDetailSerializer
        return SiteListSerializer

    @action(detail=True, methods=["get"], url_path="logos")
    def logos(self, request, pk=None):
        """Retorna los logos del sitio."""
        site = self.get_object()
        serializer = SiteLogosSerializer(
            site.logos.order_by("stack_order"), many=True
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get", "patch"], url_path="config")
    def config(self, request, pk=None):
        """Obtiene o actualiza la configuracion del sitio."""
        site = self.get_object()
        config, _ = SiteConfiguration.objects.get_or_create(site=site)

        if request.method == "GET":
            return Response(SiteConfigurationSerializer(config).data)

        # PATCH
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = SiteConfigurationSerializer(
            config, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# SiteLogosViewSet
# ---------------------------------------------------------------------------

class SiteLogosViewSet(ModelViewSet):
    """ViewSet para gestionar logos de sitios."""

    authentication_classes = AUTHENTICATION_CLASSES
    queryset = SiteLogos.objects.all().order_by("stack_order")
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        site_id = self.request.query_params.get("site")
        if site_id:
            qs = qs.filter(site_id=site_id)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsDashboardAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return SiteLogosCreateSerializer
        return SiteLogosSerializer

    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena logos en bloque."""
        serializer = ReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        updated_count = 0
        for item in serializer.validated_data:
            try:
                logo = SiteLogos.objects.get(id=item["id"])
                logo.stack_order = item["stack_order"]
                logo.save(update_fields=["stack_order"])
                updated_count += 1
            except SiteLogos.DoesNotExist:
                continue

        return Response({"success": True, "updated_count": updated_count})


# ---------------------------------------------------------------------------
# IndicatorGroupViewSet
# ---------------------------------------------------------------------------

class IndicatorGroupViewSet(ModelViewSet):
    """ViewSet para gestionar grupos de indicadores."""

    authentication_classes = AUTHENTICATION_CLASSES
    pagination_class = DashboardPagination
    queryset = IndicatorGroup.objects.select_related("site").order_by("stack_order")

    def get_queryset(self):
        qs = super().get_queryset()
        site_id = self.request.query_params.get("site")
        if site_id:
            qs = qs.filter(site_id=site_id)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve", "select_data"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsDashboardAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return IndicatorGroupCreateSerializer
        if self.action in ("update", "partial_update"):
            return IndicatorGroupUpdateSerializer
        if self.action == "retrieve":
            return IndicatorGroupDetailSerializer
        return IndicatorGroupListSerializer

    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena grupos en bloque."""
        serializer = ReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        updated_count = 0
        for item in serializer.validated_data:
            try:
                group = IndicatorGroup.objects.get(id=item["id"])
                group.stack_order = item["stack_order"]
                group.save(update_fields=["stack_order"])
                updated_count += 1
            except IndicatorGroup.DoesNotExist:
                continue

        return Response({"success": True, "updated_count": updated_count})

    @action(
        detail=True,
        methods=["get"],
        url_path="select-data",
    )
    def select_data(self, request, pk=None):
        """
        Retorna la estructura de subgrupos e indicadores del grupo
        para poblar selects en el frontend.
        """
        group = self.get_object()

        subgroups = []
        indicators = []

        if group.subgroups.exists():
            for subgroup in group.subgroups.order_by("stack_order"):
                if subgroup.indicators.exists():
                    temp = {
                        "subgroup_id": subgroup.id,
                        "subgroup_name": subgroup.name,
                        "subgroup_icon": subgroup.icon,
                        "icon_custom": (
                            subgroup.icon_custom.url
                            if subgroup.icon_custom
                            else None
                        ),
                        "indicators": [],
                    }
                    for ind in subgroup.indicators.order_by("stack_order"):
                        if ind.plot_values or ind.is_histogram:
                            temp["indicators"].append(
                                {
                                    "indicator_id": ind.id,
                                    "indicator_name": ind.name,
                                    "is_histogram": ind.is_histogram,
                                }
                            )
                    if temp["indicators"]:
                        subgroups.append(temp)
        else:
            for ind in group.indicators.order_by("stack_order"):
                if ind.plot_values or ind.is_histogram:
                    indicators.append(
                        {
                            "indicator_id": ind.id,
                            "indicator_name": ind.name,
                            "is_histogram": ind.is_histogram,
                        }
                    )

        return Response({"subgroups": subgroups, "indicators": indicators})


# ---------------------------------------------------------------------------
# SubGroupViewSet
# ---------------------------------------------------------------------------

class SubGroupViewSet(ModelViewSet):
    """ViewSet para gestionar subgrupos de indicadores."""

    authentication_classes = AUTHENTICATION_CLASSES
    queryset = SubGroup.objects.select_related("group", "group__site").order_by(
        "stack_order"
    )
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        site_id = self.request.query_params.get("site")
        group_id = self.request.query_params.get("group")
        if site_id:
            qs = qs.filter(group__site_id=site_id)
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsDashboardAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return SubGroupCreateSerializer
        if self.action in ("update", "partial_update"):
            return SubGroupUpdateSerializer
        return SubGroupSerializer

    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena subgrupos en bloque."""
        serializer = ReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        updated_count = 0
        for item in serializer.validated_data:
            try:
                subgroup = SubGroup.objects.get(id=item["id"])
                subgroup.stack_order = item["stack_order"]
                subgroup.save(update_fields=["stack_order"])
                updated_count += 1
            except SubGroup.DoesNotExist:
                continue

        return Response({"success": True, "updated_count": updated_count})


# ---------------------------------------------------------------------------
# IndicatorViewSet
# ---------------------------------------------------------------------------

class IndicatorViewSet(ModelViewSet):
    """ViewSet para gestionar indicadores geoespaciales."""

    authentication_classes = AUTHENTICATION_CLASSES
    pagination_class = DashboardPagination
    queryset = Indicator.objects.select_related(
        "site", "group", "subgroup", "layer"
    ).order_by("stack_order")

    def get_queryset(self):
        qs = super().get_queryset()
        site_id = self.request.query_params.get("site")
        group_id = self.request.query_params.get("group")
        subgroup_id = self.request.query_params.get("subgroup")
        if site_id:
            qs = qs.filter(site_id=site_id)
        if group_id:
            qs = qs.filter(group_id=group_id)
        if subgroup_id:
            qs = qs.filter(subgroup_id=subgroup_id)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve", "view_data", "get_data", "info"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsDashboardAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return IndicatorCreateSerializer
        if self.action in ("update", "partial_update"):
            return IndicatorUpdateSerializer
        if self.action == "retrieve":
            return IndicatorDetailSerializer
        return IndicatorListSerializer

    @action(detail=True, methods=["post"], url_path="build-data")
    def build_data(self, request, pk=None):
        """
        Construye la data del indicador consultando la base de datos de geonode_data.
        """
        indicator = self.get_object()

        serializer = IndicatorBuildDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        field_id = d["field_id"]
        field_one = d["field_one"]
        field_two = d.get("field_two", "")
        method = d["method"]
        categories = d["categories"]
        manual_bins_raw = d.get("manual_bins", "")

        attributes = [field_one, field_two] if field_two else field_one
        manual_bins = (
            [float(i) for i in manual_bins_raw.split(",")]
            if method == "manual" and manual_bins_raw
            else []
        )

        try:
            layer_name = indicator.layer.name
        except Exception:
            return Response(
                {"error": "El indicador no tiene una capa asociada valida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = get_data_from_db(attributes, field_id, layer_name)
        if data is None:
            return Response(
                {"error": "No se pudo obtener datos de la base de datos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        processed = process_data(data, attributes, field_id, method, categories, indicator, manual_bins)
        return Response(processed)

    @action(detail=True, methods=["post"], url_path="save-data")
    def save_data(self, request, pk=None):
        """Guarda la configuracion y valores del indicador."""
        indicator = self.get_object()

        serializer = IndicatorSaveDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        if d.get("histogram_fields") is not None:
            indicator.layer_id_field = d["field_id"]
            indicator.layer_nom_field = d["field_name"]
            indicator.high_values_percentage = d["high_values"]
            indicator.histogram_fields = d["histogram_fields"]
            indicator.colors = d["colors"]
            indicator.use_custom_colors = d["use_custom_color"]
            indicator.custom_colors = d["custom_colors"]
            indicator.plot_config = d["plot_config"]
            indicator.use_filter = d["use_filter"]
            indicator.show_general_values = d["general_values"]
            indicator.filters = d["filters"]
        else:
            indicator.layer_id_field = d["field_id"]
            indicator.use_single_field = d["single_field"]
            indicator.field_one = d["field_one"]
            indicator.field_two = d["field_two"]
            indicator.field_popup = d["field_popup"]
            indicator.category_method = d["category_method"]
            indicator.field_category = d["field_category"]
            indicator.colors = d["colors"]
            indicator.use_custom_colors = d["use_custom_color"]
            indicator.custom_colors = d["custom_colors"]
            indicator.plot_values = d["plot_values"]
            indicator.map_values = d["map_values"]
            indicator.plot_config = d["plot_config"]
            indicator.use_filter = d["use_filter"]
            indicator.filters = d["filters"]

        indicator.save()
        return Response({"indicator": indicator.id})

    @action(detail=True, methods=["get"], url_path="view-data")
    def view_data(self, request, pk=None):
        """Retorna los datos guardados del indicador con sus infoboxes."""
        indicator = self.get_object()

        data = {}
        if indicator.plot_values:
            data["plot_values"] = indicator.plot_values
            data["map_values"] = indicator.map_values
            data["plot_config"] = indicator.plot_config
            data["layer_id_field"] = indicator.layer_id_field
            data["field_popup"] = indicator.field_popup
            data["info_text"] = indicator.info_text
            data["field_one"] = indicator.field_one
            data["use_filter"] = indicator.use_filter
            data["filters"] = indicator.filters or {}
        else:
            data["histogram_fields"] = indicator.histogram_fields
            data["plot_config"] = indicator.plot_config
            data["layer_id_field"] = indicator.layer_id_field
            data["layer_nom_field"] = indicator.layer_nom_field
            data["high_values_percentage"] = indicator.high_values_percentage
            data["custom_colors"] = indicator.custom_colors
            data["info_text"] = indicator.info_text
            data["use_filter"] = indicator.use_filter
            data["show_general_values"] = indicator.show_general_values
            data["filters"] = indicator.filters or {}

        boxes = []
        for box in indicator.infoboxes.order_by("stack_order"):
            boxes.append(
                {
                    "id": box.id,
                    "field": box.field,
                    "is_percentage": box.is_percentage,
                    "field_percentage_total": box.field_percentage_total,
                    "name": box.name,
                    "icon": box.icon,
                    "icon_custom": box.icon_custom.url if box.icon_custom else None,
                    "color": box.color,
                    "size": box.size,
                    "edge_style": box.edge_style,
                    "edge_color": box.edge_color,
                    "text_color": box.text_color,
                    "order": box.stack_order,
                }
            )
        data["info_boxes"] = boxes

        return Response({"data": data})

    @action(detail=True, methods=["post"], url_path="clone")
    def clone(self, request, pk=None):
        """Clona un indicador con nuevos campos y opcionalmente sus infoboxes."""
        source = self.get_object()

        serializer = IndicatorCloneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        field_one = d["field_one"]
        field_two = d.get("field_two", "")
        attributes = [field_one, field_two] if field_two else field_one

        field_id = source.layer_id_field
        method = source.category_method
        categories = source.field_category

        try:
            layer_name = source.layer.name
        except Exception:
            return Response(
                {"error": "La capa del indicador fuente no es valida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = get_data_from_db(attributes, field_id, layer_name)
        if data is None:
            return Response(
                {"error": "No se pudo obtener datos de la base de datos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        processed = process_data(
            data, attributes, field_id, method, categories, source, []
        )

        custom_colors_list = (
            source.custom_colors.split(",")
            if source.custom_colors
            else None
        )
        color_data = assign_color(processed, source.colors, custom_colors_list)

        # Determinar stack_order segun jerarquia
        stack_order = 1
        if source.subgroup:
            stack_order = source.subgroup.indicators.count() + 1
        elif source.group:
            stack_order = source.group.indicators.count() + 1
        elif source.site:
            stack_order = source.site.indicators.count() + 1

        new_name = d.get("name") or (source.name + " clon " + str(stack_order))

        new_indicator = Indicator(
            subgroup=source.subgroup,
            group=source.group,
            site=source.site,
            name=new_name,
            plot_type=source.plot_type,
            info_text=source.info_text,
            layer=source.layer,
            layer_id_field=source.layer_id_field,
            use_single_field=source.use_single_field,
            is_histogram=source.is_histogram,
            histogram_fields=source.histogram_fields,
            field_one=field_one,
            field_two=field_two,
            field_popup=source.field_popup,
            category_method=source.category_method,
            field_category=source.field_category,
            colors=source.colors,
            use_custom_colors=source.use_custom_colors,
            custom_colors=source.custom_colors,
            use_filter=source.use_filter,
            filters=source.filters,
            plot_config=source.plot_config,
            plot_values=color_data["plot_data"],
            map_values=color_data["theming_data"],
            stack_order=stack_order,
        )
        new_indicator.save()

        if d.get("clone_boxes"):
            for box in source.infoboxes.all():
                IndicatorFieldBoxInfo(
                    indicator=new_indicator,
                    field=box.field,
                    is_percentage=box.is_percentage,
                    field_percentage_total=box.field_percentage_total,
                    name=box.name,
                    icon=box.icon,
                    color=box.color,
                    size=box.size,
                    edge_style=box.edge_style,
                    edge_color=box.edge_color,
                    text_color=box.text_color,
                    stack_order=box.stack_order,
                ).save()

        return Response({"ind_clone": new_indicator.id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena indicadores en bloque."""
        serializer = ReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        updated_count = 0
        for item in serializer.validated_data:
            try:
                ind = Indicator.objects.get(id=item["id"])
                ind.stack_order = item["stack_order"]
                ind.save(update_fields=["stack_order"])
                updated_count += 1
            except Indicator.DoesNotExist:
                continue

        return Response({"success": True, "updated_count": updated_count})

    @action(detail=False, methods=["get"], url_path="get-data")
    def get_data(self, request):
        """
        Retorna datos resumidos para multiples indicadores.

        Query param: indicator_ids=1,2,3  (ids separados por coma)
        """
        ids_raw = request.query_params.get("indicator_ids", "")
        if not ids_raw:
            return Response({"data": {}})

        try:
            ids = [int(i.strip()) for i in ids_raw.split(",") if i.strip()]
        except ValueError:
            return Response(
                {"error": "indicator_ids debe ser una lista de enteros separados por coma."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {}
        for ind_id in ids:
            try:
                ind = Indicator.objects.get(id=ind_id)
                data[ind_id] = {
                    "name": ind.name,
                    "histogram_fields": ind.histogram_fields,
                    "plot_config": ind.plot_config,
                    "layer_id_field": ind.layer_id_field,
                    "custom_colors": ind.custom_colors,
                    "info_text": ind.info_text,
                }
            except Indicator.DoesNotExist:
                continue

        return Response({"data": data})

    @action(detail=True, methods=["get"], url_path="info")
    def info(self, request, pk=None):
        """
        Retorna el info_text del indicador usando la cadena de herencia:
        subgroup → group → site.
        """
        indicator = self.get_object()

        text = None
        if indicator.subgroup and indicator.subgroup.info_text:
            text = indicator.subgroup.info_text
        elif indicator.subgroup and indicator.subgroup.group.info_text:
            text = indicator.subgroup.group.info_text
        elif indicator.subgroup and indicator.subgroup.group.site.info_text:
            text = indicator.subgroup.group.site.info_text
        elif indicator.group and indicator.group.info_text:
            text = indicator.group.info_text
        elif indicator.group and indicator.group.site.info_text:
            text = indicator.group.site.info_text
        elif indicator.site and indicator.site.info_text:
            text = indicator.site.info_text

        return Response({"info": text or "No hay informacion"})


# ---------------------------------------------------------------------------
# IndicatorFieldBoxInfoViewSet
# ---------------------------------------------------------------------------

class IndicatorFieldBoxInfoViewSet(ModelViewSet):
    """ViewSet para gestionar infoboxes de indicadores."""

    authentication_classes = AUTHENTICATION_CLASSES
    queryset = IndicatorFieldBoxInfo.objects.select_related("indicator").order_by(
        "stack_order"
    )
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        indicator_id = self.request.query_params.get("indicator")
        if indicator_id:
            qs = qs.filter(indicator_id=indicator_id)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsDashboardAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return IndicatorFieldBoxInfoCreateSerializer
        return IndicatorFieldBoxInfoSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-add/(?P<indicator_id>[0-9]+)",
    )
    def bulk_add(self, request, indicator_id=None):
        """Crea multiples infoboxes para un indicador."""
        indicator = get_object_or_404(Indicator, id=indicator_id)

        data = request.data if isinstance(request.data, list) else [request.data]
        for item in data:
            item["indicator"] = indicator.id

        serializer = IndicatorFieldBoxInfoCreateSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        created = []
        for item_data in serializer.validated_data:
            item_data.pop("indicator", None)
            box = IndicatorFieldBoxInfo(**item_data, indicator=indicator)
            box.save()
            created.append(box)

        return Response(
            IndicatorFieldBoxInfoSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-delete/(?P<indicator_id>[0-9]+)",
    )
    def bulk_delete(self, request, indicator_id=None):
        """Elimina multiples infoboxes de un indicador."""
        indicator = get_object_or_404(Indicator, id=indicator_id)

        serializer = BulkIdSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        ids = [item["id"] for item in serializer.validated_data]
        deleted_count = IndicatorFieldBoxInfo.objects.filter(
            id__in=ids, indicator=indicator
        ).delete()[0]

        return Response({"success": True, "deleted_count": deleted_count})

    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena infoboxes en bloque."""
        serializer = ReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        updated_count = 0
        for item in serializer.validated_data:
            try:
                box = IndicatorFieldBoxInfo.objects.get(id=item["id"])
                box.stack_order = item["stack_order"]
                box.save(update_fields=["stack_order"])
                updated_count += 1
            except IndicatorFieldBoxInfo.DoesNotExist:
                continue

        return Response({"success": True, "updated_count": updated_count})


# ---------------------------------------------------------------------------
# SiteConfigurationViewSet
# ---------------------------------------------------------------------------

class SiteConfigurationViewSet(ModelViewSet):
    """ViewSet para gestionar la configuracion de sitio (get_or_create por site_id)."""

    authentication_classes = AUTHENTICATION_CLASSES
    queryset = SiteConfiguration.objects.select_related("site").all()
    serializer_class = SiteConfigurationSerializer
    lookup_field = "site_id"
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        site_id = self.request.query_params.get("site")
        if site_id:
            qs = qs.filter(site_id=site_id)
        return qs

    def get_permissions(self):
        if self.action == "retrieve":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsDashboardAdmin()]

    def get_object(self):
        site_id = self.kwargs.get("site_id")
        site = get_object_or_404(Site, id=site_id)
        config, _ = SiteConfiguration.objects.get_or_create(site=site)
        return config
