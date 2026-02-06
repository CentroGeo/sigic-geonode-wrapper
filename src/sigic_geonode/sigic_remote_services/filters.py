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

import logging

from django.db.models import Exists, OuterRef
from rest_framework.filters import BaseFilterBackend

from geonode.harvesting.models import HarvestableResource
from geonode.services.models import Service

logger = logging.getLogger(__name__)


class HarvesterIdFilter(BaseFilterBackend):
    """
    Filtro para datasets por harvester_id.

    Uso: ?harvester_id=123
    """

    def filter_queryset(self, request, queryset, view):
        harvester_id = request.query_params.get("harvester_id")

        if harvester_id:
            try:
                harvester_id = int(harvester_id)
                queryset = queryset.annotate(
                    has_harvester=Exists(
                        HarvestableResource.objects.filter(
                            geonode_resource=OuterRef("resourcebase_ptr"),
                            harvester_id=harvester_id,
                        )
                    )
                ).filter(has_harvester=True)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error en HarvesterIdFilter: {e}")

        return queryset


class ServiceIdFilter(BaseFilterBackend):
    """
    Filtro para datasets por service_id.

    Uso: ?service_id=456
    """

    def filter_queryset(self, request, queryset, view):
        service_id = request.query_params.get("service_id")

        if service_id:
            try:
                service_id = int(service_id)
                service = Service.objects.filter(id=service_id).first()
                if service and service.harvester:
                    queryset = queryset.annotate(
                        has_service=Exists(
                            HarvestableResource.objects.filter(
                                geonode_resource=OuterRef("resourcebase_ptr"),
                                harvester=service.harvester,
                            )
                        )
                    ).filter(has_service=True)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error en ServiceIdFilter: {e}")

        return queryset


class OwnerFilter(BaseFilterBackend):
    """
    Filtro para servicios por owner.

    Uso: ?owner_id=1
    Si el usuario no es superusuario, solo ve sus propios servicios.
    """

    def filter_queryset(self, request, queryset, view):
        owner_id = request.query_params.get("owner_id")

        if owner_id:
            try:
                owner_id = int(owner_id)
                queryset = queryset.filter(owner_id=owner_id)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error en OwnerFilter: {e}")
        elif not request.user.is_superuser and request.user.is_authenticated:
            queryset = queryset.filter(owner=request.user)

        return queryset


class TypeFilter(BaseFilterBackend):
    """
    Filtro para servicios por tipo.

    Uso: ?type=WMS o ?type=WMS,FILE (múltiples valores separados por coma)
    """

    def filter_queryset(self, request, queryset, view):
        service_type = request.query_params.get("type")

        if service_type:
            types = [t.strip().upper() for t in service_type.split(",")]
            queryset = queryset.filter(type__in=types)

        return queryset


class NameFilter(BaseFilterBackend):
    """
    Filtro para servicios por nombre (búsqueda parcial insensible a mayúsculas).

    Uso: ?name=datos
    """

    def filter_queryset(self, request, queryset, view):
        name = request.query_params.get("name")

        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset


class TitleFilter(BaseFilterBackend):
    """
    Filtro para servicios por título (búsqueda parcial insensible a mayúsculas).

    Uso: ?title=servicio
    """

    def filter_queryset(self, request, queryset, view):
        title = request.query_params.get("title")

        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset


class CreatedRangeFilter(BaseFilterBackend):
    """
    Filtro para servicios por rango de fecha de creación.

    Uso: ?created_after=2024-01-01&created_before=2024-12-31
    Las fechas deben estar en formato ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS).
    """

    def filter_queryset(self, request, queryset, view):
        from django.utils.dateparse import parse_datetime, parse_date

        created_after = request.query_params.get("created_after")
        created_before = request.query_params.get("created_before")

        if created_after:
            try:
                dt = parse_datetime(created_after) or parse_date(created_after)
                if dt:
                    queryset = queryset.filter(created__gte=dt)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error en CreatedRangeFilter (after): {e}")

        if created_before:
            try:
                dt = parse_datetime(created_before) or parse_date(created_before)
                if dt:
                    queryset = queryset.filter(created__lte=dt)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error en CreatedRangeFilter (before): {e}")

        return queryset


class HarvesterStatusFilter(BaseFilterBackend):
    """
    Filtro para servicios por estado del harvester asociado.

    Uso: ?harvester_status=ready o ?harvester_status=ready,updating-harvestable-resources
    Valores posibles: ready, updating-harvestable-resources, performing-harvesting, etc.
    """

    def filter_queryset(self, request, queryset, view):
        harvester_status = request.query_params.get("harvester_status")

        if harvester_status:
            statuses = [s.strip().lower() for s in harvester_status.split(",")]
            queryset = queryset.filter(harvester__status__in=statuses)

        return queryset


class UrlFilter(BaseFilterBackend):
    """
    Filtro para servicios por URL (búsqueda parcial insensible a mayúsculas).

    Uso: ?url=geoserver
    """

    def filter_queryset(self, request, queryset, view):
        url = request.query_params.get("url")

        if url:
            queryset = queryset.filter(base_url__icontains=url)

        return queryset


class DescriptionFilter(BaseFilterBackend):
    """
    Filtro para servicios por descripción (búsqueda parcial insensible a mayúsculas).

    Uso: ?description=geoespacial
    """

    def filter_queryset(self, request, queryset, view):
        description = request.query_params.get("description")

        if description:
            queryset = queryset.filter(description__icontains=description)

        return queryset


class AbstractFilter(BaseFilterBackend):
    """
    Filtro para servicios por abstract (búsqueda parcial insensible a mayúsculas).

    Uso: ?abstract=infraestructura
    """

    def filter_queryset(self, request, queryset, view):
        abstract = request.query_params.get("abstract")

        if abstract:
            queryset = queryset.filter(abstract__icontains=abstract)

        return queryset
