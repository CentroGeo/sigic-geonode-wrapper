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
Monkey patching para extender funcionalidades de GeoNode.

Agrega las siguientes funcionalidades:
- HarvesterViewSet: Filtro por default_owner, campo service_id en respuestas
- WmsServiceHandler/ArcMapServiceHandler: Corrige bug donde harvester_id no se guardaba
"""

import logging

from rest_framework import status
from rest_framework.response import Response

from geonode.harvesting.api.views import HarvesterViewSet
from geonode.harvesting.models import Harvester
from geonode.services.models import Service
from geonode.services.serviceprocessors.wms import WmsServiceHandler
from geonode.services.serviceprocessors.arcgis import ArcMapServiceHandler

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

    # Aplicar patches a HarvesterViewSet
    HarvesterViewSet.get_queryset = custom_get_queryset
    HarvesterViewSet.list = custom_list
    HarvesterViewSet.retrieve = custom_retrieve
    HarvesterViewSet._patched_by_sigic = True


# =============================================================================
# Patch para WmsServiceHandler y ArcMapServiceHandler
# Bug: harvester_id no se guardaba al crear servicios remotos
# =============================================================================

if not getattr(WmsServiceHandler, "_patched_by_sigic", False):
    _orig_wms_create_geonode_service = WmsServiceHandler.create_geonode_service

    def patched_wms_create_geonode_service(self, owner, parent=None):
        """
        Corrige bug donde el harvester se asignaba pero no se persistía.
        """
        instance = _orig_wms_create_geonode_service(self, owner, parent)
        if instance and instance.harvester and instance.pk:
            instance.save(update_fields=["harvester"])
            logger.debug(
                f"[SIGIC Patch] Harvester {instance.harvester.id} guardado "
                f"para servicio {instance.id}"
            )
        return instance

    WmsServiceHandler.create_geonode_service = patched_wms_create_geonode_service
    WmsServiceHandler._patched_by_sigic = True


if not getattr(ArcMapServiceHandler, "_patched_by_sigic", False):
    _orig_arc_create_geonode_service = ArcMapServiceHandler.create_geonode_service

    def patched_arc_create_geonode_service(self, owner, parent=None):
        """
        Corrige bug donde el harvester se asignaba pero no se persistía.
        """
        instance = _orig_arc_create_geonode_service(self, owner, parent)
        if instance and instance.harvester and instance.pk:
            instance.save(update_fields=["harvester"])
            logger.debug(
                f"[SIGIC Patch] Harvester {instance.harvester.id} guardado "
                f"para servicio ArcGIS {instance.id}"
            )
        return instance

    ArcMapServiceHandler.create_geonode_service = patched_arc_create_geonode_service
    ArcMapServiceHandler._patched_by_sigic = True
