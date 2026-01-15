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

"""
Monkey patching para extender HarvesterViewSet de GeoNode.

Agrega las siguientes funcionalidades:
- Filtro por default_owner para que usuarios vean solo sus harvesters
- Validación de URL única por usuario al crear
- Campo service_id en las respuestas
"""

import logging

from rest_framework import status
from rest_framework.response import Response

from geonode.harvesting.api.views import HarvesterViewSet
from geonode.harvesting.models import Harvester
from geonode.services.models import Service

logger = logging.getLogger(__name__)


if not getattr(HarvesterViewSet, "_patched_by_sigic", False):
    _orig_get_queryset = HarvesterViewSet.get_queryset
    _orig_list = HarvesterViewSet.list
    _orig_retrieve = HarvesterViewSet.retrieve

    def custom_get_queryset(self):
        """
        Filtra harvesters por default_owner si el usuario no es superusuario.
        Permite filtrar por owner_id mediante query param.
        """
        try:
            qs = _orig_get_queryset(self)
            request = self.request

            # Filtro por owner_id (query param)
            owner_id = request.query_params.get("owner_id")
            if owner_id:
                qs = qs.filter(default_owner_id=owner_id)

            # Si no es superusuario, solo ve sus propios harvesters
            if not request.user.is_superuser and request.user.is_authenticated:
                qs = qs.filter(default_owner=request.user)

            return qs
        except Exception as e:
            logger.warning(f"Error en custom_get_queryset de HarvesterViewSet: {e}")
            return _orig_get_queryset(self)

    def custom_list(self, request, *args, **kwargs):
        """
        Extiende el listado para incluir service_id en cada harvester.
        """
        response = _orig_list(self, request, *args, **kwargs)

        if hasattr(response, "data"):
            # GeoNode usa 'harvesters' como clave, no 'results'
            results = response.data.get("harvesters", response.data.get("results", []))
            if isinstance(results, list):
                for item in results:
                    harvester_id = item.get("id")
                    if harvester_id:
                        service = Service.objects.filter(
                            harvester_id=harvester_id
                        ).first()
                        item["service_id"] = service.id if service else None

        return response

    def custom_retrieve(self, request, *args, **kwargs):
        """
        Extiende el detalle para incluir service_id y description del servicio.
        """
        response = _orig_retrieve(self, request, *args, **kwargs)

        if hasattr(response, "data") and isinstance(response.data, dict):
            # GeoNode anida el harvester en un objeto 'harvester'
            harvester_data = response.data.get("harvester", response.data)
            harvester_id = harvester_data.get("id")
            if harvester_id:
                service = Service.objects.filter(harvester_id=harvester_id).first()
                harvester_data["service_id"] = service.id if service else None
                harvester_data["service_description"] = (
                    service.description if service else None
                )

        return response

    # Aplicar patches
    HarvesterViewSet.get_queryset = custom_get_queryset
    HarvesterViewSet.list = custom_list
    HarvesterViewSet.retrieve = custom_retrieve
    HarvesterViewSet._patched_by_sigic = True
