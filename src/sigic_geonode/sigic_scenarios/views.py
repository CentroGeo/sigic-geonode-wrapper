# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este codigo fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene credito de autoria, pero la titularidad del codigo
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
ViewSets para la gestion de escenarios, escenas, capas y marcadores.

Expone una API REST completa con operaciones CRUD, operaciones en bloque
(reordenamiento, creacion y eliminacion masiva) y subida de imagenes.
"""

import datetime
import io
import logging
import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from PIL import Image
from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

from .models import Scenario, Scene, SceneLayer, SceneMarker
from .permissions import IsScenarioOwner
from .serializers import (
    BulkIdSerializer,
    ScenarioCreateSerializer,
    ScenarioDetailSerializer,
    ScenarioListSerializer,
    ScenarioUpdateSerializer,
    SceneBasicSerializer,
    SceneCreateSerializer,
    SceneLayerCreateSerializer,
    SceneLayerReorderSerializer,
    SceneLayerSerializer,
    SceneLayerStyleUpdateSerializer,
    SceneLayerUpdateSerializer,
    SceneMarkerCreateSerializer,
    SceneMarkerSerializer,
    SceneMarkerUpdateSerializer,
    SceneReorderSerializer,
    SceneSerializer,
    SceneUpdateSerializer,
)

logger = logging.getLogger(__name__)


class ScenarioPagination(PageNumberPagination):
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


# Clases de autenticacion reutilizables
AUTHENTICATION_CLASSES = [
    BasicAuthentication,
    SessionAuthentication,
    OAuth2Authentication,
    KeycloakJWTAuthentication,
]


def _check_scenario_owner(scenario, user):
    """Verifica que el usuario sea el propietario del escenario."""
    if scenario.owner != user:
        raise PermissionDenied("No autorizado")


# ---------------------------------------------------------------------------
# ScenarioViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(
        summary="Lista escenarios",
        description=(
            "Retorna escenarios publicos y, si el usuario esta autenticado, "
            "tambien los propios. Soporta paginacion."
        ),
        tags=["Escenarios"],
    ),
    retrieve=extend_schema(
        summary="Detalle de un escenario",
        description="Retorna el detalle de un escenario con lista basica de escenas.",
        tags=["Escenarios"],
    ),
    create=extend_schema(
        summary="Crea un nuevo escenario",
        description="Crea un escenario asignando al usuario autenticado como propietario.",
        tags=["Escenarios"],
    ),
    update=extend_schema(
        summary="Actualiza un escenario",
        description="Actualiza todos los campos del escenario. Solo el propietario puede hacerlo.",
        tags=["Escenarios"],
    ),
    partial_update=extend_schema(
        summary="Actualiza parcialmente un escenario",
        description="Actualiza campos individuales del escenario.",
        tags=["Escenarios"],
    ),
    destroy=extend_schema(
        summary="Elimina un escenario",
        description="Elimina el escenario y todas sus escenas, capas y marcadores asociados.",
        tags=["Escenarios"],
    ),
)
class ScenarioViewSet(ModelViewSet):
    """ViewSet para gestionar escenarios narrativos."""

    authentication_classes = AUTHENTICATION_CLASSES
    pagination_class = ScenarioPagination

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsScenarioOwner()]

    def get_serializer_class(self):
        if self.action == "create":
            return ScenarioCreateSerializer
        if self.action in ("update", "partial_update"):
            return ScenarioUpdateSerializer
        if self.action == "retrieve":
            return ScenarioDetailSerializer
        return ScenarioListSerializer

    def get_queryset(self):
        qs = Scenario.objects.select_related("owner").order_by("-created_at")
        if not self.request.user.is_authenticated:
            return qs.filter(is_public=True)
        return qs.filter(Q(is_public=True) | Q(owner=self.request.user))

    def perform_create(self, serializer):
        # Valores por defecto para scenes_layout_styles si no se proporcionan
        layout = serializer.validated_data.get("scenes_layout_styles")
        if not layout:
            serializer.validated_data["scenes_layout_styles"] = {
                "text_panel": 50,
                "map_panel": 50,
                "timeline_position": "bottom",
            }
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        _check_scenario_owner(serializer.instance, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _check_scenario_owner(instance, self.request.user)
        instance.delete()

    @extend_schema(
        summary="Sube imagen de portada",
        description="Sube una imagen como portada del escenario. Solo el propietario puede hacerlo.",
        request={"multipart/form-data": {"type": "object", "properties": {"card_image": {"type": "string", "format": "binary"}}}},
        responses={200: ScenarioDetailSerializer},
        tags=["Escenarios"],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="upload-image",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request, pk=None):
        """Sube imagen de portada para el escenario."""
        scenario = self.get_object()
        _check_scenario_owner(scenario, request.user)

        image_file = request.FILES.get("card_image")
        if not image_file:
            return Response(
                {"detail": "Falta el archivo 'card_image'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scenario.card_image.save(image_file.name, image_file)
        serializer = ScenarioDetailSerializer(scenario, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Lista escenas del escenario",
        description="Retorna todas las escenas del escenario ordenadas por stack_order.",
        responses={200: SceneSerializer(many=True)},
        tags=["Escenarios"],
    )
    @action(detail=True, methods=["get"], url_path="scenes")
    def list_scenes(self, request, pk=None):
        """Lista las escenas de un escenario."""
        scenario = self.get_object()
        scenes = scenario.scenes.order_by("stack_order")
        serializer = SceneSerializer(scenes, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# SceneViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(
        summary="Lista escenas",
        description="Retorna todas las escenas accesibles para el usuario.",
        tags=["Escenas"],
    ),
    retrieve=extend_schema(
        summary="Detalle de una escena",
        description="Retorna la escena con sus capas y marcadores anidados.",
        tags=["Escenas"],
    ),
    create=extend_schema(
        summary="Crea una nueva escena",
        description="Crea una escena dentro de un escenario. Solo el propietario del escenario puede hacerlo.",
        tags=["Escenas"],
    ),
    update=extend_schema(
        summary="Actualiza una escena",
        tags=["Escenas"],
    ),
    partial_update=extend_schema(
        summary="Actualiza parcialmente una escena",
        tags=["Escenas"],
    ),
    destroy=extend_schema(
        summary="Elimina una escena",
        tags=["Escenas"],
    ),
)
class SceneViewSet(ModelViewSet):
    """ViewSet para gestionar escenas dentro de escenarios."""

    authentication_classes = AUTHENTICATION_CLASSES

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return SceneCreateSerializer
        if self.action in ("update", "partial_update"):
            return SceneUpdateSerializer
        return SceneSerializer

    def get_queryset(self):
        qs = Scene.objects.select_related("scenario", "scenario__owner")
        if not self.request.user.is_authenticated:
            return qs.filter(scenario__is_public=True)
        return qs.filter(
            Q(scenario__is_public=True) | Q(scenario__owner=self.request.user)
        )

    def perform_create(self, serializer):
        scenario = serializer.validated_data["scenario"]
        _check_scenario_owner(scenario, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        _check_scenario_owner(serializer.instance.scenario, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _check_scenario_owner(instance.scenario, self.request.user)
        instance.delete()

    @extend_schema(
        summary="Reordena escenas en bloque",
        description="Actualiza el stack_order de multiples escenas de forma atomica.",
        request=SceneReorderSerializer(many=True),
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}, "updated_count": {"type": "integer"}}}},
        tags=["Escenas"],
    )
    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena escenas en bloque."""
        serializer = SceneReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data
        if not items:
            return Response(
                {"success": False, "message": "No se proporcionaron escenas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verificar permisos sobre la primera escena
        first_scene = get_object_or_404(Scene, id=items[0]["id"])
        _check_scenario_owner(first_scene.scenario, request.user)

        updated_count = 0
        for item in items:
            try:
                scene = Scene.objects.get(id=item["id"])
                scene.stack_order = item["stack_order"]
                scene.save(update_fields=["stack_order"])
                updated_count += 1
            except Scene.DoesNotExist:
                continue
        return Response({"success": True, "updated_count": updated_count})

    @extend_schema(
        summary="Lista capas de una escena",
        description="Retorna las capas de la escena ordenadas por stack_order.",
        responses={200: SceneLayerSerializer(many=True)},
        tags=["Escenas"],
    )
    @action(detail=True, methods=["get"], url_path="layers")
    def list_layers(self, request, pk=None):
        """Lista las capas de una escena."""
        scene = self.get_object()
        layers = scene.layers.order_by("stack_order")
        serializer = SceneLayerSerializer(layers, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# SceneLayerViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(
        summary="Lista capas de escena",
        tags=["Capas de Escena"],
    ),
    retrieve=extend_schema(
        summary="Detalle de una capa",
        tags=["Capas de Escena"],
    ),
    create=extend_schema(
        summary="Crea una capa de escena",
        tags=["Capas de Escena"],
    ),
    update=extend_schema(
        summary="Actualiza una capa",
        tags=["Capas de Escena"],
    ),
    partial_update=extend_schema(
        summary="Actualiza parcialmente una capa",
        tags=["Capas de Escena"],
    ),
    destroy=extend_schema(
        summary="Elimina una capa",
        tags=["Capas de Escena"],
    ),
)
class SceneLayerViewSet(ModelViewSet):
    """ViewSet para gestionar capas asociadas a escenas."""

    authentication_classes = AUTHENTICATION_CLASSES

    def get_permissions(self):
        if self.action in ("list", "retrieve", "by_scene"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return SceneLayerCreateSerializer
        if self.action in ("update", "partial_update"):
            return SceneLayerUpdateSerializer
        return SceneLayerSerializer

    def get_queryset(self):
        qs = SceneLayer.objects.select_related(
            "scene", "scene__scenario", "scene__scenario__owner"
        )
        if not self.request.user.is_authenticated:
            return qs.filter(scene__scenario__is_public=True)
        return qs.filter(
            Q(scene__scenario__is_public=True)
            | Q(scene__scenario__owner=self.request.user)
        )

    def perform_create(self, serializer):
        scene = serializer.validated_data["scene"]
        _check_scenario_owner(scene.scenario, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        _check_scenario_owner(serializer.instance.scene.scenario, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _check_scenario_owner(instance.scene.scenario, self.request.user)
        instance.delete()

    @extend_schema(
        summary="Lista capas por escena",
        description="Retorna todas las capas de una escena especifica.",
        parameters=[
            OpenApiParameter(name="scene_id", location="path", type=int, description="ID de la escena"),
        ],
        responses={200: SceneLayerSerializer(many=True)},
        tags=["Capas de Escena"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"by-scene/(?P<scene_id>[0-9]+)",
    )
    def by_scene(self, request, scene_id=None):
        """Lista capas de una escena especifica."""
        scene = get_object_or_404(Scene, id=scene_id)

        # Verificar permisos de lectura
        if not scene.scenario.is_public:
            if not request.user.is_authenticated or scene.scenario.owner != request.user:
                raise PermissionDenied("No autorizado")

        layers = scene.layers.order_by("stack_order")
        serializer = SceneLayerSerializer(layers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Crea capas en bloque",
        description="Crea multiples capas para una escena en una sola peticion.",
        parameters=[
            OpenApiParameter(name="scene_id", location="path", type=int, description="ID de la escena"),
        ],
        request=SceneLayerCreateSerializer(many=True),
        responses={201: SceneLayerSerializer(many=True)},
        tags=["Capas de Escena"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-add/(?P<scene_id>[0-9]+)",
    )
    def bulk_add(self, request, scene_id=None):
        """Crea multiples capas para una escena."""
        scene = get_object_or_404(Scene, id=scene_id)
        _check_scenario_owner(scene.scenario, request.user)

        # Inyectar scene_id en cada item para que el serializer lo valide
        data = request.data if isinstance(request.data, list) else [request.data]
        for item in data:
            item["scene"] = scene.id

        serializer = SceneLayerCreateSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        created = []
        for item_data in serializer.validated_data:
            item_data.pop("scene", None)
            layer = SceneLayer(**item_data, scene=scene)
            layer.save()
            created.append(layer)

        return Response(
            SceneLayerSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Actualiza estilo de una capa",
        description="Actualiza unicamente los campos de estilo (style, style_title) de una capa.",
        request=SceneLayerStyleUpdateSerializer,
        responses={200: SceneLayerSerializer},
        tags=["Capas de Escena"],
    )
    @action(detail=True, methods=["put", "patch"], url_path="update-style")
    def update_style(self, request, pk=None):
        """Actualiza solo el estilo de una capa."""
        layer = self.get_object()
        _check_scenario_owner(layer.scene.scenario, request.user)

        serializer = SceneLayerStyleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for attr, value in serializer.validated_data.items():
            setattr(layer, attr, value)
        layer.save()
        return Response(SceneLayerSerializer(layer).data)

    @extend_schema(
        summary="Reordena capas en bloque",
        description="Actualiza el stack_order de multiples capas de forma atomica.",
        request=SceneLayerReorderSerializer(many=True),
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}, "updated_count": {"type": "integer"}}}},
        tags=["Capas de Escena"],
    )
    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena capas en bloque."""
        serializer = SceneLayerReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data
        if not items:
            return Response(
                {"success": False, "message": "No se proporcionaron capas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        first_layer = get_object_or_404(SceneLayer, id=items[0]["id"])
        _check_scenario_owner(first_layer.scene.scenario, request.user)

        updated_count = 0
        for item in items:
            try:
                layer = SceneLayer.objects.get(id=item["id"])
                layer.stack_order = item["stack_order"]
                layer.save(update_fields=["stack_order"])
                updated_count += 1
            except SceneLayer.DoesNotExist:
                continue
        return Response({"success": True, "updated_count": updated_count})

    @extend_schema(
        summary="Elimina capas en bloque",
        description="Elimina multiples capas de una escena. Reporta errores individuales.",
        parameters=[
            OpenApiParameter(name="scene_id", location="path", type=int, description="ID de la escena"),
        ],
        request=BulkIdSerializer(many=True),
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}, "deleted_count": {"type": "integer"}, "errors": {"type": "array", "items": {"type": "string"}}}}},
        tags=["Capas de Escena"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-delete/(?P<scene_id>[0-9]+)",
    )
    def bulk_delete(self, request, scene_id=None):
        """Elimina multiples capas de una escena."""
        scene = get_object_or_404(Scene, id=scene_id)
        _check_scenario_owner(scene.scenario, request.user)

        serializer = BulkIdSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        ids = [item["id"] for item in serializer.validated_data]
        errors = []
        deleted_count = 0

        for layer_id in ids:
            try:
                layer = SceneLayer.objects.get(id=layer_id)
                if layer.scene_id != scene.id:
                    errors.append(f"Capa {layer_id} no pertenece a esta escena")
                    continue
                layer.delete()
                deleted_count += 1
            except SceneLayer.DoesNotExist:
                errors.append(f"Capa {layer_id} no existe")

        if errors:
            logger.warning("Errores en bulk delete de capas: %s", errors)

        return Response(
            {"success": True, "deleted_count": deleted_count, "errors": errors}
        )


# ---------------------------------------------------------------------------
# SceneMarkerViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(
        summary="Lista marcadores de escena",
        tags=["Marcadores de Escena"],
    ),
    retrieve=extend_schema(
        summary="Detalle de un marcador",
        tags=["Marcadores de Escena"],
    ),
    create=extend_schema(
        summary="Crea un marcador",
        tags=["Marcadores de Escena"],
    ),
    update=extend_schema(
        summary="Actualiza un marcador",
        tags=["Marcadores de Escena"],
    ),
    partial_update=extend_schema(
        summary="Actualiza parcialmente un marcador",
        tags=["Marcadores de Escena"],
    ),
    destroy=extend_schema(
        summary="Elimina un marcador",
        tags=["Marcadores de Escena"],
    ),
)
class SceneMarkerViewSet(ModelViewSet):
    """ViewSet para gestionar marcadores sobre el mapa de una escena."""

    authentication_classes = AUTHENTICATION_CLASSES

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return SceneMarkerCreateSerializer
        if self.action in ("update", "partial_update"):
            return SceneMarkerUpdateSerializer
        return SceneMarkerSerializer

    def get_queryset(self):
        qs = SceneMarker.objects.select_related(
            "scene", "scene__scenario", "scene__scenario__owner"
        )
        if not self.request.user.is_authenticated:
            return qs.filter(scene__scenario__is_public=True)
        return qs.filter(
            Q(scene__scenario__is_public=True)
            | Q(scene__scenario__owner=self.request.user)
        )

    def perform_create(self, serializer):
        scene = serializer.validated_data["scene"]
        _check_scenario_owner(scene.scenario, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        _check_scenario_owner(serializer.instance.scene.scenario, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _check_scenario_owner(instance.scene.scenario, self.request.user)
        logger.info("Eliminando marcador %s", instance.id)
        instance.delete()

    @extend_schema(
        summary="Lista marcadores por escena",
        description="Retorna todos los marcadores de una escena especifica.",
        parameters=[
            OpenApiParameter(name="scene_id", location="path", type=int, description="ID de la escena"),
        ],
        responses={200: SceneMarkerSerializer(many=True)},
        tags=["Marcadores de Escena"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"by-scene/(?P<scene_id>[0-9]+)",
    )
    def by_scene(self, request, scene_id=None):
        """Lista marcadores de una escena especifica."""
        scene = get_object_or_404(Scene, id=scene_id)

        if not scene.scenario.is_public:
            if not request.user.is_authenticated or scene.scenario.owner != request.user:
                raise PermissionDenied("No autorizado")

        markers = scene.markers.all()
        serializer = SceneMarkerSerializer(markers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Crea marcadores en bloque",
        description="Crea multiples marcadores para una escena en una sola peticion.",
        parameters=[
            OpenApiParameter(name="scene_id", location="path", type=int, description="ID de la escena"),
        ],
        request=SceneMarkerCreateSerializer(many=True),
        responses={201: SceneMarkerSerializer(many=True)},
        tags=["Marcadores de Escena"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-add/(?P<scene_id>[0-9]+)",
    )
    def bulk_add(self, request, scene_id=None):
        """Crea multiples marcadores para una escena."""
        scene = get_object_or_404(Scene, id=scene_id)
        _check_scenario_owner(scene.scenario, request.user)

        # Inyectar scene_id en cada item para que el serializer lo valide
        data = request.data if isinstance(request.data, list) else [request.data]
        for item in data:
            item["scene"] = scene.id

        serializer = SceneMarkerCreateSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        created = []
        for item_data in serializer.validated_data:
            item_data.pop("scene", None)
            marker = SceneMarker(**item_data, scene=scene)
            marker.save()
            created.append(marker)

        return Response(
            SceneMarkerSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Elimina marcadores en bloque",
        description="Elimina multiples marcadores de una escena.",
        parameters=[
            OpenApiParameter(name="scene_id", location="path", type=int, description="ID de la escena"),
        ],
        request=BulkIdSerializer(many=True),
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}, "deleted_count": {"type": "integer"}}}},
        tags=["Marcadores de Escena"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-delete/(?P<scene_id>[0-9]+)",
    )
    def bulk_delete(self, request, scene_id=None):
        """Elimina multiples marcadores de una escena."""
        scene = get_object_or_404(Scene, id=scene_id)
        _check_scenario_owner(scene.scenario, request.user)

        serializer = BulkIdSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        ids = [item["id"] for item in serializer.validated_data]
        deleted_count = SceneMarker.objects.filter(
            id__in=ids, scene=scene
        ).delete()[0]

        return Response({"success": True, "deleted_count": deleted_count})


# ---------------------------------------------------------------------------
# ImageUploadView
# ---------------------------------------------------------------------------

# Configuracion de subida de imagenes
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_IMAGE_DIMENSION = 2048  # pixeles
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "webp"]


class ImageUploadView(APIView):
    """
    Endpoint para subir imagenes (compatible con editores de texto enriquecido).

    Valida tamanio y formato del archivo, redimensiona imagenes mayores a 2048px,
    convierte RGBA a RGB cuando es necesario, y organiza los archivos por fecha.
    """

    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Sube una imagen",
        description=(
            "Sube y procesa una imagen. Maximo 5MB. "
            "Formatos: jpg, jpeg, png, gif, webp. "
            "Las imagenes mayores a 2048px se redimensionan automaticamente."
        ),
        request={"multipart/form-data": {"type": "object", "properties": {"upload": {"type": "string", "format": "binary"}}}},
        responses={200: {"type": "object", "properties": {"url": {"type": "string"}}}},
        tags=["Uploads"],
    )
    def post(self, request):
        upload = request.FILES.get("upload")
        if not upload:
            return Response(
                {"error": {"message": "No se envio archivo"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar tamanio
        if upload.size > MAX_FILE_SIZE:
            return Response(
                {"error": {"message": f"El archivo es demasiado grande. Maximo {MAX_FILE_SIZE // 1024 // 1024}MB"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar extension
        file_extension = upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
        if file_extension not in ALLOWED_EXTENSIONS:
            return Response(
                {"error": {"message": f"Formato no permitido. Usa: {', '.join(ALLOWED_EXTENSIONS)}"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Abrir y verificar que sea una imagen valida
            image = Image.open(upload.file)
            image.verify()

            # Reabrir (verify() cierra el archivo)
            upload.file.seek(0)
            image = Image.open(upload.file)

            # Redimensionar si excede el maximo
            if image.width > MAX_IMAGE_DIMENSION or image.height > MAX_IMAGE_DIMENSION:
                image.thumbnail(
                    (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
                    Image.Resampling.LANCZOS,
                )

                output = io.BytesIO()

                # Convertir RGBA a RGB si es necesario (para JPEG)
                if image.mode == "RGBA" and file_extension in ("jpg", "jpeg"):
                    rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[3])
                    image = rgb_image

                # Guardar con calidad optimizada
                format_name = "JPEG" if file_extension in ("jpg", "jpeg") else file_extension.upper()
                image.save(output, format=format_name, quality=85, optimize=True)
                output.seek(0)
                upload.file = output
            else:
                upload.file.seek(0)

            # Generar ruta con subcarpeta por fecha y nombre unico
            today = datetime.date.today()
            subfolder = f"{today.year}/{today.month:02d}"
            unique_filename = f"{subfolder}/{uuid.uuid4().hex[:8]}_{upload.name}"

            fs = FileSystemStorage()
            filename = fs.save(unique_filename, upload.file)

            file_url = request.build_absolute_uri(
                os.path.join(settings.MEDIA_URL, filename)
            )

            return Response({"url": file_url})

        except Exception as e:
            logger.exception("Error al procesar imagen")
            return Response(
                {"error": {"message": f"Error al procesar la imagen: {str(e)}"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
