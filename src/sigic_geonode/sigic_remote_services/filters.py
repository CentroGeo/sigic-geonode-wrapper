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
