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
- IsAdminOrListOnly: Permite que owners accedan a sus propios harvesters
- WmsServiceHandler/ArcMapServiceHandler: Corrige bug donde harvester_id no se guardaba,
  desactiva delete_orphan_resources_automatically
- BaseHarvesterWorker: Fuerza permisos owner-only tras cada cosecha
- ArcgisHarvesterWorker/OgcWmsHarvester: Sufija name/store/alternate con _h{harvester_id}
  para que cada usuario sea propietario de su propia copia del recurso cosechado
"""

import logging

from rest_framework import status
from rest_framework.response import Response

from geonode.harvesting.api.views import HarvesterViewSet, IsAdminOrListOnly
from geonode.harvesting.harvesters.arcgis import ArcgisHarvesterWorker
from geonode.harvesting.harvesters.base import BaseHarvesterWorker
from geonode.harvesting.harvesters.wms import OgcWmsHarvester
from geonode.harvesting.models import Harvester
from geonode.resource.manager import resource_manager
from geonode.services.models import Service
from geonode.services.serviceprocessors.wms import WmsServiceHandler
from geonode.services.serviceprocessors.arcgis import ArcMapServiceHandler

logger = logging.getLogger(__name__)

# Permisos owner-only: ningún grupo ni usuario extra tiene acceso.
# El owner obtiene sus permisos implícitamente a través de resource_manager.
_OWNER_ONLY_PERMISSIONS = {"users": {}, "groups": {}}


# =============================================================================
# Patch para IsAdminOrListOnly - Permite que owners accedan a sus harvesters
# =============================================================================

if not getattr(IsAdminOrListOnly, "_patched_by_sigic", False):
    _orig_has_permission = IsAdminOrListOnly.has_permission

    def patched_has_permission(self, request, view):
        """
        Extiende permisos para permitir que el owner del harvester acceda.

        Permisos originales de GeoNode:
        - Superusuarios: acceso total
        - Otros usuarios: solo pueden listar

        Permisos extendidos por SIGIC:
        - Superusuarios: acceso total
        - Owner del harvester: puede ver detalle, actualizar y operar su harvester
        - Otros usuarios: solo pueden listar
        """
        # Superusuarios tienen acceso total
        if request.user.is_superuser:
            return True

        # Listar siempre está permitido (el queryset filtra por owner)
        if view.action == "list":
            return True

        # Para otras acciones, verificar si el usuario es owner del harvester
        if request.user.is_authenticated and view.action in [
            "retrieve", "update", "partial_update", "destroy",
            "harvestable_resources", "update_harvestable_resources",
            "perform_harvesting"
        ]:
            # Obtener el harvester_id de la URL
            harvester_pk = view.kwargs.get("pk") or view.kwargs.get("harvester_id")
            if harvester_pk:
                try:
                    harvester = Harvester.objects.get(pk=harvester_pk)
                    if harvester.default_owner == request.user:
                        return True
                except Harvester.DoesNotExist:
                    pass

        return False

    IsAdminOrListOnly.has_permission = patched_has_permission
    IsAdminOrListOnly._patched_by_sigic = True
    logger.info("[SIGIC Patch] IsAdminOrListOnly permisos extendidos para owners")


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
        También desactiva delete_orphan_resources_automatically para evitar
        que la re-cosecha de un usuario elimine recursos de otros usuarios
        que compartan la misma URL de servicio.
        Establece default_access_permissions a owner-only.
        """
        instance = _orig_wms_create_geonode_service(self, owner, parent)
        if instance and instance.harvester and instance.pk:
            instance.save(update_fields=["harvester"])
            logger.debug(
                f"[SIGIC Patch] Harvester {instance.harvester.id} guardado "
                f"para servicio {instance.id}"
            )
            update_fields = []
            if instance.harvester.delete_orphan_resources_automatically:
                instance.harvester.delete_orphan_resources_automatically = False
                update_fields.append("delete_orphan_resources_automatically")
                logger.debug(
                    f"[SIGIC Patch] delete_orphan_resources_automatically "
                    f"desactivado para harvester {instance.harvester.id}"
                )
            if instance.harvester.default_access_permissions != _OWNER_ONLY_PERMISSIONS:
                instance.harvester.default_access_permissions = _OWNER_ONLY_PERMISSIONS
                update_fields.append("default_access_permissions")
                logger.debug(
                    f"[SIGIC Patch] default_access_permissions owner-only "
                    f"establecido para harvester {instance.harvester.id}"
                )
            if update_fields:
                instance.harvester.save(update_fields=update_fields)
        return instance

    WmsServiceHandler.create_geonode_service = patched_wms_create_geonode_service
    WmsServiceHandler._patched_by_sigic = True


if not getattr(ArcMapServiceHandler, "_patched_by_sigic", False):
    _orig_arc_create_geonode_service = ArcMapServiceHandler.create_geonode_service

    def patched_arc_create_geonode_service(self, owner, parent=None):
        """
        Corrige bug donde el harvester se asignaba pero no se persistía.
        También desactiva delete_orphan_resources_automatically para evitar
        que la re-cosecha de un usuario elimine recursos de otros usuarios
        que compartan la misma URL de servicio.
        Establece default_access_permissions a owner-only.
        """
        instance = _orig_arc_create_geonode_service(self, owner, parent)
        if instance and instance.harvester and instance.pk:
            instance.save(update_fields=["harvester"])
            logger.debug(
                f"[SIGIC Patch] Harvester {instance.harvester.id} guardado "
                f"para servicio ArcGIS {instance.id}"
            )
            update_fields = []
            if instance.harvester.delete_orphan_resources_automatically:
                instance.harvester.delete_orphan_resources_automatically = False
                update_fields.append("delete_orphan_resources_automatically")
                logger.debug(
                    f"[SIGIC Patch] delete_orphan_resources_automatically "
                    f"desactivado para harvester ArcGIS {instance.harvester.id}"
                )
            if instance.harvester.default_access_permissions != _OWNER_ONLY_PERMISSIONS:
                instance.harvester.default_access_permissions = _OWNER_ONLY_PERMISSIONS
                update_fields.append("default_access_permissions")
                logger.debug(
                    f"[SIGIC Patch] default_access_permissions owner-only "
                    f"establecido para harvester ArcGIS {instance.harvester.id}"
                )
            if update_fields:
                instance.harvester.save(update_fields=update_fields)
        return instance

    ArcMapServiceHandler.create_geonode_service = patched_arc_create_geonode_service
    ArcMapServiceHandler._patched_by_sigic = True


# =============================================================================
# Patch para BaseHarvesterWorker
# Fuerza permisos owner-only en Guardian tras cada cosecha, independientemente
# del estado de GeoFence. Garantiza que los recursos cosechados sean visibles
# únicamente para el owner y superusuarios.
# =============================================================================

if not getattr(BaseHarvesterWorker, "_patched_by_sigic_permissions", False):
    _orig_finalize_resource_update = BaseHarvesterWorker.finalize_resource_update

    def patched_finalize_resource_update(
        self, geonode_resource, harvested_info, harvestable_resource
    ):
        """
        Llama a la finalización estándar y luego fuerza permisos owner-only
        en Django (Guardian), sin importar si GeoFence tuvo errores.
        """
        try:
            _orig_finalize_resource_update(
                self, geonode_resource, harvested_info, harvestable_resource
            )
        except Exception as e:
            logger.warning(
                f"[SIGIC Patch] finalize_resource_update original falló "
                f"(posiblemente GeoFence): {e}"
            )

        if geonode_resource is None:
            return

        try:
            owner = harvestable_resource.harvester.default_owner
            resource_manager.set_permissions(
                geonode_resource.uuid,
                instance=geonode_resource,
                permissions=_OWNER_ONLY_PERMISSIONS,
                created=False,
            )
            logger.debug(
                f"[SIGIC Patch] Permisos owner-only aplicados al recurso "
                f"{geonode_resource.id} (owner: {owner})"
            )
        except Exception as e:
            logger.warning(
                f"[SIGIC Patch] No se pudieron forzar permisos owner-only "
                f"en recurso {geonode_resource.id}: {e}"
            )

    BaseHarvesterWorker.finalize_resource_update = patched_finalize_resource_update
    BaseHarvesterWorker._patched_by_sigic_permissions = True
    logger.info("[SIGIC Patch] BaseHarvesterWorker permisos owner-only activados")


# =============================================================================
# Patch para ArcgisHarvesterWorker y OgcWmsHarvester
# Sufija name, store y alternate con _h{harvester_id} para que cada usuario
# tenga su propia fila en layers_dataset como propietario, evitando el
# IntegrityError del unique constraint (store, workspace, name) cuando múltiples
# usuarios cosechan el mismo servicio remoto.
# =============================================================================

def _patch_harvester_resource_defaults(worker_class, label):
    """
    Aplica el patch de unicidad por harvester a get_geonode_resource_defaults.

    Modifica name, store y alternate para incluir el sufijo _h{harvester_id},
    garantizando que cada harvester genere filas únicas en layers_dataset.
    El campo ows_url no se modifica: sigue apuntando al servicio externo real.
    """
    if getattr(worker_class, "_patched_by_sigic_unique_name", False):
        return

    _orig_get_defaults = worker_class.get_geonode_resource_defaults

    def patched_get_geonode_resource_defaults(self, harvested_info, harvestable_resource):
        defaults = _orig_get_defaults(self, harvested_info, harvestable_resource)
        suffix = f"_h{self.harvester_id}"

        if "name" in defaults:
            defaults["name"] = f"{defaults['name']}{suffix}"

        if "store" in defaults:
            defaults["store"] = f"{defaults['store']}{suffix}"

        if "alternate" in defaults:
            # alternate tiene formato "workspace:name" — actualizar solo la parte del name
            parts = defaults["alternate"].split(":", 1)
            if len(parts) == 2:
                defaults["alternate"] = f"{parts[0]}:{parts[1]}{suffix}"
            else:
                defaults["alternate"] = f"{defaults['alternate']}{suffix}"

        return defaults

    worker_class.get_geonode_resource_defaults = patched_get_geonode_resource_defaults
    worker_class._patched_by_sigic_unique_name = True
    logger.info(f"[SIGIC Patch] {label} get_geonode_resource_defaults con unicidad por harvester")


_patch_harvester_resource_defaults(ArcgisHarvesterWorker, "ArcgisHarvesterWorker")
_patch_harvester_resource_defaults(OgcWmsHarvester, "OgcWmsHarvester")
