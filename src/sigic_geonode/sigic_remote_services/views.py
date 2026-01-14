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

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from geonode.layers.api.views import DatasetViewSet
from geonode.layers.models import Dataset
from geonode.services.models import Service
from geonode.harvesting.models import HarvestableResource

from .filters import HarvesterIdFilter, ServiceIdFilter
from .serializers import (
    ServiceCreateSerializer,
    ServiceResponseSerializer,
    ServiceDetailSerializer,
)
from sigic_geonode.sigic_remote_services.file_handler import FileServiceHandler

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Lista servicios remotos del usuario",
        description="Retorna todos los servicios remotos registrados por el usuario autenticado.",
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
            "puede existir para diferentes usuarios."
        ),
        tags=["Servicios Remotos"],
    ),
)
class RemoteServiceViewSet(ViewSet):
    """
    ViewSet para gestionar servicios remotos (Harvesters).

    Permite al usuario registrar URLs de archivos remotos (CSV, JSON, GeoJSON, etc.)
    que serán procesados por el sistema de harvesting de GeoNode.

    Validaciones:
    - Una URL solo puede registrarse una vez por usuario
    - La misma URL puede existir para diferentes usuarios
    - Extensiones permitidas: csv, json, geojson, xls, xlsx
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Lista todos los servicios remotos del usuario autenticado."""
        services = Service.objects.filter(owner=request.user).select_related(
            "harvester"
        )
        serializer = ServiceResponseSerializer(services, many=True)
        return Response({"count": services.count(), "results": serializer.data})

    def retrieve(self, request, pk=None):
        """Obtiene el detalle de un servicio remoto."""
        try:
            service = Service.objects.select_related("harvester").get(
                pk=pk, owner=request.user
            )
        except Service.DoesNotExist:
            return Response(
                {"error": "Servicio no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ServiceDetailSerializer(service)
        return Response(serializer.data)

    def create(self, request):
        """
        Registra un nuevo servicio remoto.

        El frontend debe validar previamente que la URL es accesible
        y del tipo correcto antes de llamar a este endpoint.
        """
        serializer = ServiceCreateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data["url"]
        description = serializer.validated_data.get("description", "")

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
                handler = FileServiceHandler(url)

                if not handler.probe():
                    return Response(
                        {
                            "error": (
                                "URL no válida o extensión no soportada. "
                                "Extensiones permitidas: csv, json, geojson, xls, xlsx"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                service = handler.create_geonode_service(owner=request.user)

                if description:
                    service.description = description
                    service.save(update_fields=["description"])

        except Exception as e:
            logger.error(f"Error al crear servicio remoto: {e}")
            return Response(
                {"error": f"Error al crear el servicio: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = ServiceResponseSerializer(service)
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

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        return serializer_class

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
