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
ViewSet para gestionar servicios remotos (Services) vía API REST.

Este módulo expone el modelo Service de GeoNode que no tiene endpoint REST nativo.
Permite crear servicios con validación de URL única por usuario.
"""

import logging
import math

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from geonode.base.api.pagination import GeoNodeApiPagination
from geonode.layers.api.views import DatasetViewSet
from geonode.services.models import Service
from geonode.services import enumerations as services_enumerations
from geonode.services.serviceprocessors import get_service_handler
from geonode.harvesting.models import Harvester, HarvestableResource

from .filters import (
    HarvesterIdFilter,
    ServiceIdFilter,
    OwnerFilter,
    TypeFilter,
    NameFilter,
    TitleFilter,
    CreatedRangeFilter,
    HarvesterStatusFilter,
    UrlFilter,
    DescriptionFilter,
    AbstractFilter,
)
from .serializers import (
    ServiceCreateSerializer,
    ServiceListSerializer,
    ServiceDetailSerializer,
)
from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Lista servicios remotos",
        description=(
            "Retorna los servicios remotos con soporte para paginación, ordenamiento y filtros. "
            "Usuarios no superusuarios solo ven sus propios servicios."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                description="Número de página (comienza en 1)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="page_size",
                description="Cantidad de resultados por página (máximo 100, por defecto 10)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="sort",
                description=(
                    "Campo de ordenamiento. Prefijo '-' para orden descendente. "
                    "Campos permitidos: created, name, title, type. Ejemplo: -created"
                ),
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="owner_id",
                description="Filtrar por ID del propietario",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="type",
                description="Filtrar por tipo de servicio (WMS, FILE, etc.). Múltiples valores separados por coma.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="name",
                description="Filtrar por nombre (búsqueda parcial, insensible a mayúsculas)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="title",
                description="Filtrar por título (búsqueda parcial, insensible a mayúsculas)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="created_after",
                description="Filtrar servicios creados después de esta fecha (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="url",
                description="Filtrar por URL (búsqueda parcial, insensible a mayúsculas)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="description",
                description="Filtrar por descripción (búsqueda parcial, insensible a mayúsculas)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="abstract",
                description="Filtrar por abstract (búsqueda parcial, insensible a mayúsculas)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="created_before",
                description="Filtrar servicios creados antes de esta fecha (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="harvester_status",
                description=(
                    "Filtrar por estado del harvester (ready, updating-harvestable-resources, "
                    "performing-harvesting). Múltiples valores separados por coma."
                ),
                required=False,
                type=str,
            ),
        ],
        tags=["Servicios Remotos"],
    ),
    retrieve=extend_schema(
        summary="Detalle de un servicio remoto",
        description="Retorna el detalle de un servicio remoto incluyendo información del harvester.",
        tags=["Servicios Remotos"],
    ),
    create=extend_schema(
        summary="Registra un nuevo servicio remoto",
        description=(
            "Crea un nuevo servicio remoto asociado al usuario autenticado. "
            "Una URL solo puede registrarse una vez por usuario, pero la misma URL "
            "puede existir para diferentes usuarios. "
            "Tipos soportados: WMS, GN_WMS, REST_MAP, REST_IMG, FILE (csv, json, geojson, xls, xlsx). "
            "Si type=AUTO, se detectará automáticamente."
        ),
        tags=["Servicios Remotos"],
    ),
    partial_update=extend_schema(
        summary="Actualiza parcialmente un servicio remoto",
        description=(
            "Permite actualizar campos del servicio como descripción. "
            "Solo el propietario del servicio o un superusuario puede actualizarlo."
        ),
        tags=["Servicios Remotos"],
    ),
)
class ServiceViewSet(ViewSet):
    """
    ViewSet para gestionar servicios remotos.

    Expone el modelo Service de GeoNode que no tiene endpoint REST nativo.
    Permite crear servicios con validación de URL única por usuario.
    """

    authentication_classes = [
        BasicAuthentication,
        SessionAuthentication,
        OAuth2Authentication,
        KeycloakJWTAuthentication,
    ]
    permission_classes = [IsAuthenticated]
    pagination_class = GeoNodeApiPagination
    filter_backends = [
        OwnerFilter,
        TypeFilter,
        NameFilter,
        TitleFilter,
        UrlFilter,
        DescriptionFilter,
        AbstractFilter,
        CreatedRangeFilter,
        HarvesterStatusFilter,
    ]

    # Campos permitidos para ordenamiento
    ALLOWED_SORT_FIELDS = {"created", "name", "title", "type", "-created", "-name", "-title", "-type"}
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    def get_queryset(self):
        """Retorna queryset filtrado por owner si no es superusuario."""
        qs = Service.objects.all().select_related("harvester", "owner")

        if not self.request.user.is_superuser and self.request.user.is_authenticated:
            qs = qs.filter(owner=self.request.user)

        owner_id = self.request.query_params.get("owner_id")
        if owner_id:
            try:
                qs = qs.filter(owner_id=int(owner_id))
            except (ValueError, TypeError):
                pass

        return qs

    def list(self, request):
        """Lista todos los servicios remotos del usuario con paginación, ordenamiento y filtros."""
        queryset = self.get_queryset()

        # Aplicar filtros
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)

        # Aplicar ordenamiento
        sort_field = request.query_params.get("sort", "-created")
        if sort_field in self.ALLOWED_SORT_FIELDS:
            queryset = queryset.order_by(sort_field)
        else:
            queryset = queryset.order_by("-created")

        # Total antes de paginar
        total_count = queryset.count()

        # Aplicar paginación
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")

        if page is not None:
            try:
                page = max(1, int(page))
                page_size = min(
                    self.MAX_PAGE_SIZE,
                    max(1, int(page_size)) if page_size else self.DEFAULT_PAGE_SIZE,
                )
                offset = (page - 1) * page_size
                queryset = queryset[offset : offset + page_size]
            except (ValueError, TypeError):
                page = 1
                page_size = self.DEFAULT_PAGE_SIZE
                queryset = queryset[: page_size]
        else:
            page = None
            page_size = None

        serializer = ServiceListSerializer(queryset, many=True)

        response_data = {
            "count": total_count,
            "results": serializer.data,
        }

        # Agregar información de paginación si se solicitó
        if page is not None:
            total_pages = math.ceil(total_count / page_size) if page_size > 0 else 1
            response_data["page"] = page
            response_data["page_size"] = page_size
            response_data["total_pages"] = total_pages

        return Response(response_data)

    def retrieve(self, request, pk=None):
        """Obtiene el detalle de un servicio remoto."""
        try:
            service = self.get_queryset().get(pk=pk)
        except Service.DoesNotExist:
            return Response(
                {"error": "Servicio no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ServiceDetailSerializer(service)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """Actualiza parcialmente un servicio remoto (solo descripción)."""
        try:
            service = self.get_queryset().get(pk=pk)
        except Service.DoesNotExist:
            return Response(
                {"error": "Servicio no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verificar permisos: solo el owner o superusuario puede actualizar
        if not request.user.is_superuser and service.owner != request.user:
            return Response(
                {"error": "No tienes permiso para modificar este servicio"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Limpiar valores "None" que vienen del bug de GeoNode
        # GeoNode guarda str(None) = "None" cuando el WMS no devuelve título
        if service.title == "None":
            service.title = ""
            updated_fields = ["title"]
        else:
            updated_fields = []

        if "description" in request.data:
            # description: CharField max_length=255
            service.description = request.data["description"][:255]
            if "description" not in updated_fields:
                updated_fields.append("description")

        if "abstract" in request.data:
            # abstract: TextField max_length=2000 - para descripciones largas
            service.abstract = request.data["abstract"][:2000]
            if "abstract" not in updated_fields:
                updated_fields.append("abstract")

        if "title" in request.data:
            # title: CharField max_length=255
            service.title = request.data["title"][:255]
            if "title" not in updated_fields:
                updated_fields.append("title")

        # Permitir asociar harvester manualmente por ID
        if "harvester_id" in request.data:
            harvester_id = request.data["harvester_id"]
            if harvester_id:
                try:
                    harvester = Harvester.objects.get(id=int(harvester_id))
                    service.harvester = harvester
                    updated_fields.append("harvester")
                except (Harvester.DoesNotExist, ValueError, TypeError):
                    return Response(
                        {"error": f"Harvester con ID {harvester_id} no encontrado"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Si se envía harvester_id como null, desasociar
                service.harvester = None
                updated_fields.append("harvester")

        # Si no tiene harvester y no se especificó uno, intentar asociar automáticamente
        if not service.harvester and "harvester_id" not in request.data:
            self._associate_harvester(service)

        if updated_fields:
            try:
                service.save(update_fields=updated_fields)
            except Exception as e:
                logger.error(f"Error al actualizar servicio: {e}")
                return Response(
                    {"error": f"Error al actualizar: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        response_serializer = ServiceDetailSerializer(service)
        return Response(response_serializer.data)

    def _associate_harvester(self, service):
        """
        Intenta asociar un harvester al servicio buscando por URL.

        Busca un harvester cuyo remote_url coincida con el base_url del servicio.
        Si encuentra uno, actualiza la relación en ambas direcciones.
        """
        if service.harvester:
            return service.harvester

        # Buscar harvester por URL exacta o con variaciones comunes
        base_url = service.base_url.rstrip("/")
        harvester = Harvester.objects.filter(remote_url=base_url).first()

        if not harvester:
            # Intentar con trailing slash
            harvester = Harvester.objects.filter(remote_url=f"{base_url}/").first()

        if not harvester:
            # Intentar sin trailing slash si el original lo tenía
            harvester = Harvester.objects.filter(
                remote_url=service.base_url
            ).first()

        if harvester:
            service.harvester = harvester
            service.save(update_fields=["harvester"])
            logger.info(
                f"Harvester {harvester.id} asociado al servicio {service.id}"
            )

        return harvester

    def create(self, request):
        """
        Registra un nuevo servicio remoto.

        Soporta múltiples tipos de servicios:
        - WMS: Web Map Service
        - GN_WMS: GeoNode Web Map Service
        - REST_MAP: ArcGIS REST MapServer
        - REST_IMG: ArcGIS REST ImageServer
        - FILE: Archivos (csv, json, geojson, xls, xlsx)
        - AUTO/OWS: Detección automática
        """
        serializer = ServiceCreateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data["url"]
        service_type = serializer.validated_data.get("type", "AUTO")
        title = serializer.validated_data.get("title", "")
        name = serializer.validated_data.get("name", "")
        description = serializer.validated_data.get("description", "")
        abstract = serializer.validated_data.get("abstract", "")

        existing = Service.objects.filter(base_url=url, owner=request.user).first()

        if existing:
            return Response(
                {
                    "error": "Ya existe un servicio con esta URL para tu usuario.",
                    "existing_service_id": existing.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Mapear tipo a enumeración de GeoNode
                type_mapping = {
                    "AUTO": services_enumerations.AUTO,
                    "OWS": services_enumerations.OWS,
                    "WMS": services_enumerations.WMS,
                    "GN_WMS": services_enumerations.GN_WMS,
                    "REST_MAP": services_enumerations.REST_MAP,
                    "REST_IMG": services_enumerations.REST_IMG,
                    "FILE": "FILE",
                }
                geonode_type = type_mapping.get(service_type, services_enumerations.AUTO)

                # Obtener el handler apropiado para el tipo de servicio
                handler = get_service_handler(
                    base_url=url,
                    service_type=geonode_type,
                )

                if not handler.probe():
                    return Response(
                        {
                            "error": (
                                "No se pudo conectar al servicio o el tipo no es válido. "
                                "Verifique la URL y el tipo de servicio."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                service = handler.create_geonode_service(owner=request.user)

                # Buscar y asociar harvester si no está asociado
                self._associate_harvester(service)

                # Sobrescribir campos si se enviaron valores
                # También limpiar título "None" del bug de GeoNode
                updated_fields = []

                if title:
                    service.title = title[:255]
                    updated_fields.append("title")
                elif service.title == "None":
                    # Limpiar el bug de GeoNode que guarda str(None)
                    service.title = ""
                    updated_fields.append("title")

                if name:
                    service.name = name[:255]
                    updated_fields.append("name")

                if description:
                    service.description = description[:255]
                    updated_fields.append("description")

                if abstract:
                    service.abstract = abstract[:2000]
                    updated_fields.append("abstract")

                if updated_fields:
                    service.save(update_fields=updated_fields)

        except Exception as e:
            logger.error(f"Error al crear servicio remoto: {e}")
            return Response(
                {"error": f"Error al crear el servicio: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = ServiceListSerializer(service)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        summary="Lista datasets de servicios remotos",
        description="Retorna datasets filtrados por harvester_id o service_id.",
        parameters=[
            OpenApiParameter(
                name="harvester_id",
                description="Filtrar por ID del harvester",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="service_id",
                description="Filtrar por ID del servicio",
                required=False,
                type=int,
            ),
        ],
        tags=["Servicios Remotos"],
    ),
)
class RemoteDatasetViewSet(DatasetViewSet):
    """
    ViewSet para datasets de servicios remotos.

    Extiende DatasetViewSet de GeoNode con filtros adicionales:
    - harvester_id: Filtrar por ID del harvester
    - service_id: Filtrar por ID del servicio
    """

    filter_backends = [HarvesterIdFilter, ServiceIdFilter] + list(
        DatasetViewSet.filter_backends
    )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        if isinstance(response.data, dict) and "resources" in response.data:
            for resource in response.data["resources"]:
                pk = resource.get("pk")
                if pk:
                    hr = HarvestableResource.objects.filter(
                        geonode_resource_id=pk
                    ).first()
                    if hr:
                        resource["harvester_id"] = hr.harvester_id
                        service = Service.objects.filter(
                            harvester_id=hr.harvester_id
                        ).first()
                        resource["service_id"] = service.id if service else None
                    else:
                        resource["harvester_id"] = None
                        resource["service_id"] = None

        return response
