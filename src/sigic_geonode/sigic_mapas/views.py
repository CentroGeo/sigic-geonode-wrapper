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
ViewSets para la gestion de mapas, y capas.

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

from .models import SigicMap, MapLayer
from .permissions import IsMapOwner
from .serializers import (
    BulkIdSerializer,
    SigicMapListSerializer,
    SigicMapDetailSerializer,
    SigicMapCreateSerializer,
    SigicMapUpdateSerializer,
    MapLayerSerializer,
    MapLayerCreateSerializer,
    MapLayerUpdateSerializer,
    MapLayerStyleUpdateSerializer,
    MapLayerReorderSerializer,
)

logger = logging.getLogger(__name__)

class SigicMapPagination(PageNumberPagination):
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


def _check_map_owner(mapa, user):
    """Verifica que el usuario sea el propietario del mapa."""
    if mapa.owner != user:
        raise PermissionDenied("No autorizado")
    

@extend_schema_view(
    list=extend_schema(
        summary="Lista mapas",
        description=(
            "Retorna los mapas creados y, si el usuario esta autenticado, "
            "tambien los propios. Soporta paginacion."
        ),
        tags=["Mapas"],
    ),
    retrieve=extend_schema(
        summary="Detalle de un mapa",
        description="Retorna el detalle de un mapa con lista basica de capas.",
        tags=["Mapas"],
    ),
    create=extend_schema(
        summary="Crea un nuevo mapa",
        description="Crea un mapa asignando al usuario autenticado como propietario.",
        tags=["Mapas"],
    ),
    update=extend_schema(
        summary="Actualiza un mapa",
        description="Actualiza todos los campos del mapa. Solo el propietario puede hacerlo.",
        tags=["Mapas"],
    ),
    partial_update=extend_schema(
        summary="Actualiza parcialmente un mapa",
        description="Actualiza campos individuales del mapa.",
        tags=["Mapas"],
    ),
    destroy=extend_schema(
        summary="Elimina un mapa",
        description="Elimina el mapa y todas sus capas y marcadores asociados.",
        tags=["Mapas"],
    ),
)
class SigicMapViewSet(ModelViewSet):
    """ViewSet para gestionar mapas."""

    authentication_classes = AUTHENTICATION_CLASSES
    pagination_class = SigicMapPagination

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsMapOwner()]

    def get_serializer_class(self):
        if self.action == "create":
            return SigicMapCreateSerializer
        if self.action in ("update", "partial_update"):
            return SigicMapUpdateSerializer
        if self.action == "retrieve":
            return SigicMapDetailSerializer
        return SigicMapListSerializer

    def get_queryset(self):
        qs = SigicMap.objects.select_related("owner").order_by("-created_at")
        if not self.request.user.is_authenticated:
            return qs.filter(is_public=True)
        return qs.filter(Q(is_public=True) | Q(owner=self.request.user))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = SigicMapDetailSerializer(
            serializer.instance, context={"request": request}
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        _check_map_owner(serializer.instance, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _check_map_owner(instance, self.request.user)
        instance.delete()

    @extend_schema(
        summary="Sube imagen de portada (preview) para el mapa",
        description="Sube una imagen como previsualización del mapa. Solo el propietario puede hacerlo.",
        request={"multipart/form-data": {"type": "object", "properties": {"card_image": {"type": "string", "format": "binary"}}}},
        responses={200: SigicMapDetailSerializer},
        tags=["Mapas"],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="upload-image",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request, pk=None):
        """Sube imagen de previsualización para el mapa."""
        mapa = self.get_object()
        _check_map_owner(mapa, request.user)

        image_file = request.FILES.get("card_image")
        if not image_file:
            return Response(
                {"detail": "Falta el archivo 'card_image'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        mapa.preview.save(image_file.name, image_file)
        serializer = SigicMapDetailSerializer(mapa, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Lista capas del mapa",
        description="Retorna todas las capas del mapa ordenadas por stack_order.",
        responses={200: MapLayerSerializer(many=True)},
        tags=["Mapas"],
    )
    @action(detail=True, methods=["get"], url_path="layers")
    def list_layers(self, request, pk=None):
        """Lista las capas de un mapa."""
        mapa = self.get_object()
        layers = mapa.layers.order_by("stack_order")
        serializer = MapLayerSerializer(layers, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="Lista capas de mapa",
        tags=["Capas de Mapa"],
    ),
    retrieve=extend_schema(
        summary="Detalle de una capa",
        tags=["Capas de Mapa"],
    ),
    create=extend_schema(
        summary="Crea una capa de mapa",
        tags=["Capas de Mapa"],
    ),
    update=extend_schema(
        summary="Actualiza una capa",
        tags=["Capas de Mapa"],
    ),
    partial_update=extend_schema(
        summary="Actualiza parcialmente una capa",
        tags=["Capas de Mapa"],
    ),
    destroy=extend_schema(
        summary="Elimina una capa",
        tags=["Capas de Mapa"],
    ),
)
class MapLayerViewSet(ModelViewSet):
    """ViewSet para gestionar capas asociadas a mapas."""

    authentication_classes = AUTHENTICATION_CLASSES

    def get_permissions(self):
        if self.action in ("list", "retrieve", "by_map"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return MapLayerCreateSerializer
        if self.action in ("update", "partial_update"):
            return MapLayerUpdateSerializer
        return MapLayerSerializer

    def get_queryset(self):
        qs = MapLayer.objects.select_related(
            "map", "map__owner"
        )
        return qs

    def perform_create(self, serializer):
        mapa = serializer.validated_data["map"]
        _check_map_owner(mapa, self.request.user)
        serializer.save()

    def perform_update(self, serializer):
        _check_map_owner(serializer.instance.map, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _check_map_owner(instance.map, self.request.user)
        instance.delete()

    @extend_schema(
        summary="Lista capas por mapa",
        description="Retorna todas las capas de un mapa especifico.",
        parameters=[
            OpenApiParameter(name="map_id", location="path", type=int, description="ID del mapa"),
        ],
        responses={200: MapLayerSerializer(many=True)},
        tags=["Capas de Mapa"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"by-map/(?P<map_id>[0-9]+)",
    )
    def by_map(self, request, map_id=None):
        """Lista capas de un mapa especifico."""
        mapa = get_object_or_404(SigicMap, id=map_id)

        layers = mapa.layers.order_by("stack_order")
        serializer = MapLayerSerializer(layers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Crea capas en bloque",
        description="Crea multiples capas para un mapa en una sola peticion.",
        parameters=[
            OpenApiParameter(name="map_id", location="path", type=int, description="ID del mapa"),
        ],
        request=MapLayerCreateSerializer(many=True),
        responses={201: MapLayerSerializer(many=True)},
        tags=["Capas de Mapa"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-add/(?P<scene_id>[0-9]+)",
    )
    def bulk_add(self, request, scene_id=None):
        """Crea multiples capas para un mapa."""
        mapa = get_object_or_404(SigicMap, id=scene_id)
        _check_map_owner(mapa, request.user)

        # Inyectar scene_id en cada item para que el serializer lo valide
        data = request.data if isinstance(request.data, list) else [request.data]
        for item in data:
            item["map"] = mapa.id

        serializer = MapLayerCreateSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        created = []
        for item_data in serializer.validated_data:
            item_data.pop("map", None)
            layer = MapLayer(**item_data, map=mapa)
            layer.save()
            created.append(layer)

        return Response(
            MapLayerSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Actualiza estilo de una capa",
        description="Actualiza unicamente los campo de estilo (style) de una capa.",
        request=MapLayerStyleUpdateSerializer,
        responses={200: MapLayerSerializer},
        tags=["Capas de Mapa"],
    )
    @action(detail=True, methods=["put", "patch"], url_path="update-style")
    def update_style(self, request, pk=None):
        """Actualiza solo el estilo de una capa."""
        layer = self.get_object()
        _check_map_owner(layer.map, request.user)

        serializer = MapLayerStyleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for attr, value in serializer.validated_data.items():
            setattr(layer, attr, value)
        layer.save()
        return Response(MapLayerSerializer(layer).data)

    @extend_schema(
        summary="Reordena capas en bloque",
        description="Actualiza el stack_order de multiples capas de forma atomica.",
        request=MapLayerReorderSerializer(many=True),
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}, "updated_count": {"type": "integer"}}}},
        tags=["Capas de Mapa"],
    )
    @action(detail=False, methods=["post"], url_path="bulk-reorder")
    def bulk_reorder(self, request):
        """Reordena capas en bloque."""
        serializer = MapLayerReorderSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data
        if not items:
            return Response(
                {"success": False, "message": "No se proporcionaron capas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        first_layer = get_object_or_404(MapLayer, id=items[0]["id"])
        _check_map_owner(first_layer.map, request.user)

        updated_count = 0
        for item in items:
            try:
                layer = MapLayer.objects.get(id=item["id"])
                layer.stack_order = item["stack_order"]
                layer.save(update_fields=["stack_order"])
                updated_count += 1
            except MapLayer.DoesNotExist:
                continue
        return Response({"success": True, "updated_count": updated_count})

    @extend_schema(
        summary="Elimina capas en bloque",
        description="Elimina multiples capas de un mapa. Reporta errores individuales.",
        parameters=[
            OpenApiParameter(name="map_id", location="path", type=int, description="ID del mapa"),
        ],
        request=BulkIdSerializer(many=True),
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}, "deleted_count": {"type": "integer"}, "errors": {"type": "array", "items": {"type": "string"}}}}},
        tags=["Capas de Mapa"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"bulk-delete/(?P<map_id>[0-9]+)",
    )
    def bulk_delete(self, request, map_id=None):
        """Elimina multiples capas de un mapa."""
        mapa = get_object_or_404(SigicMap, id=map_id)
        _check_map_owner(mapa, request.user)

        serializer = BulkIdSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        ids = [item["id"] for item in serializer.validated_data]
        errors = []
        deleted_count = 0

        for layer_id in ids:
            try:
                layer = MapLayer.objects.get(id=layer_id)
                if layer.map != mapa:
                    errors.append(f"Capa {layer_id} no pertenece a este mapa")
                    continue
                layer.delete()
                deleted_count += 1
            except MapLayer.DoesNotExist:
                errors.append(f"Capa {layer_id} no existe")

        if errors:
            logger.warning("Errores en bulk delete de capas: %s", errors)

        return Response(
            {"success": True, "deleted_count": deleted_count, "errors": errors}
        )

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
