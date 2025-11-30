# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Colaboradores: Fernando Valle
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from geonode.base.api.views import ResourceBaseViewSet
from geonode.base.models import ResourceBase
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .filters import MultiWordSearchFilter, SigicFilters, SigicOrderingFilter
from .serializers import SigicResourceShortSerializer


class SigicResourceBaseViewSet(ResourceBaseViewSet):
    """
    Extiende ResourceBaseViewSet con filtros personalizados Sigic. En esta clase se
    mantienen los backends nativos de Geonode  y los personalizados, en los cuales
    es importantes saber:
    - En el SigicFilters usamos `pop()` para consumir únicamente nuestros filtros
    custom (institution, year, has_geometry, extension).
    - Esto evita que DynamicFilterBackend intente procesarlos y marque error:
    "Invalid filter field".
    - Así se logra un "arreglo" entre los dos backs:
    - Los filtros nativos de GeoNode siguen funcionando (ej: category.identifier).
    - Los filtros custom se procesan optimizados, ya que son operaciones directas en BD."""

    filter_backends = [
        SigicFilters,
        MultiWordSearchFilter,
        SigicOrderingFilter,
    ] + ResourceBaseViewSet.filter_backends


class SigicResourceShortViewSet(SigicResourceBaseViewSet):
    """
    Vista reducida con menos campos en la respuesta.
    Reutiliza los filtros optimizados de SigicResourceBaseViewSet.
    """

    serializer_class = SigicResourceShortSerializer


class ResourceKeywordTagViewSet(ViewSet):
    """
    Gestiona los *keywords* (etiquetas) asociados a un ResourceBase de GeoNode.

    Este ViewSet proporciona un endpoint estable y desacoplado del
    serializador interno de GeoNode. Permite consultar, agregar, reemplazar
    o eliminar *keywords* sin pasar por DynamicRest ni por el
    ResourceBaseSerializer, evitando errores de parseo y problemas en PATCH.

    Endpoints soportados:

    - **GET /api/v2/resources/{resource_pk}/keywordtags/**
        Devuelve la lista actual de keywords asociados al resource.

    - **POST /api/v2/resources/{resource_pk}/keywordtags/**
        Agrega nuevos keywords al resource. Los existentes se preservan.
        Los keywords inexistentes se crean automáticamente.

    - **PUT /api/v2/resources/{resource_pk}/keywordtags/**
        Reemplaza completamente el conjunto de keywords del resource por los
        proporcionados en el cuerpo de la petición.

    - **DELETE /api/v2/resources/{resource_pk}/keywordtags/**
        Elimina la asociación entre el resource y los keywords indicados.
        No elimina los keywords del catálogo global, solo la relación.

    Notas:
        - Requiere autenticación.
        - El cuerpo de las peticiones debe ser SIEMPRE una lista JSON
          de cadenas, por ejemplo:
              ["bosque", "morelia", "mexico"]
        - Se basa en Taggit: los keywords se crean automáticamente si no existen.
        - No modifica vocabularios ni tesauros; únicamente relaciones del resource.
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def _get_resource(self, pk):
        """
        Obtiene el ResourceBase solicitado o lanza HTTP 404.

        Args:
            pk (int): ID del ResourceBase.

        Returns:
            ResourceBase: Instancia del resource solicitado.

        Raises:
            Http404: Si no existe el resource.
        """
        return get_object_or_404(ResourceBase, pk=pk)

    def _check_view_perm(self, resource, user):
        """
        Verifica si un usuario tiene permiso para *ver* el resource.

        Reglas aplicadas
        ----------------
        1. Si el resource está publicado **y** aprobado (`is_published` + `is_approved`),
           el acceso es público y se permite a cualquier usuario, autenticado o no.

        2. Si el usuario está autenticado, se le permite el acceso únicamente si
           posee el permiso `base.view_resourcebase` sobre el `resourcebase_ptr`
           del resource.

        3. Si ninguna condición se cumple, se lanza `PermissionDenied`.

        Parámetros
        ----------
        resource : ResourceBase
            El resource cuyo acceso se está validando.

        user : User
            Usuario que realiza la solicitud.

        Excepciones
        -----------
        PermissionDenied
            Cuando el usuario no tiene permiso para acceder al recurso.

        Notas
        -----
        Este método centraliza la lógica de lectura, alineándola con la forma en que
        GeoNode maneja la visibilidad de los recursos.
        """

        # Caso 1: acceso público
        if resource.is_published and resource.is_approved:
            return

        # Caso 2: usuario autenticado con permiso de lectura
        if user and user.is_authenticated:
            if user.has_perm("base.view_resourcebase", resource.resourcebase_ptr):
                return

        raise PermissionDenied("You do not have permission to view this resource.")

    def _check_edit_perm(self, resource, user):
        """
        Verifica si un usuario tiene permisos para modificar los keywords del resource.

        Reglas aplicadas
        ----------------
        1. El usuario debe estar autenticado.
        2. El superuser siempre puede editar.
        3. El dueño del recurso siempre puede editar.
        4. Si no es dueño, debe tener el permiso `base.change_resourcebase`.

        Si ninguna condición se cumple, se lanza `PermissionDenied`.
        """

        if not (user and user.is_authenticated):
            raise PermissionDenied("Authentication required.")

        # Superuser → acceso total
        if user.is_superuser:
            return

        # El dueño del resource puede editar metadata
        if hasattr(resource, "owner") and resource.owner == user:
            return

        # Permiso oficial para editar metadata (incluye keywords)
        if user.has_perm("base.change_resourcebase", resource):
            return

        raise PermissionDenied("You do not have permission to modify keywords.")

    @extend_schema(
        methods=["get"],
        summary="Obtiene los keywords del resource",
        responses={
            200: {"application/json": {"type": "array", "items": {"type": "string"}}}
        },
        description="Devuelve la lista de keywords asociados al resource.",
    )
    @extend_schema(
        methods=["post"],
        summary="Agrega keywords al resource",
        request={"application/json": {"type": "array", "items": {"type": "string"}}},
        responses={
            200: {"application/json": {"type": "array", "items": {"type": "string"}}}
        },
        examples=[
            OpenApiExample("Agregar etiquetas", value=["bosque", "morelia"]),
        ],
    )
    @extend_schema(
        methods=["put"],
        summary="Reemplaza completamente los keywords del resource",
        request={"application/json": {"type": "array", "items": {"type": "string"}}},
        responses={
            200: {"application/json": {"type": "array", "items": {"type": "string"}}}
        },
        examples=[
            OpenApiExample("Reemplazo total", value=["bosque", "mexico"]),
        ],
    )
    @action(
        detail=False,  # o detail=True según cómo tengas el router
        methods=["get", "post", "put"],
        url_path="keywordtags",
    )
    def keywordtags(self, request, resource_pk=None):
        """
        Gestión de keywords de un resource.

        - GET  → Lista todos los keywords asociados al resource.
        - POST → Agrega uno o varios keywords sin eliminar los existentes,
                 aunque sea solo una debe enviarse en forma de array.
        - PUT  → Reemplaza TODOS los keywords con la lista enviada.

        El cuerpo para POST y PUT debe ser una lista JSON de cadenas.

        Returns:
            Response: Lista JSON con los nombres finales de los keywords.
        """
        ds = self._get_resource(resource_pk)

        # ============================================================
        # GET → solo lectura, no requiere permiso de edición
        # ============================================================
        if request.method == "GET":
            return Response(list(ds.keywords.names()))

        # Para POST y PUT sí necesitas permiso de edición
        self._check_edit_perm(ds, request.user)

        if not isinstance(request.data, list):
            raise ValidationError("El cuerpo debe ser una lista de cadenas.")

        # ============================================================
        # POST → Agregar sin borrar
        # ============================================================
        if request.method == "POST":
            for kw in request.data:
                ds.keywords.add(kw)

        # ============================================================
        # PUT → Reemplazo total
        # ============================================================
        elif request.method == "PUT":
            ds.keywords.set([])  # limpia todo
            for kw in request.data:
                ds.keywords.add(kw)

        return Response(list(ds.keywords.names()))

    @action(
        detail=False,
        methods=["delete"],
        url_path=r"(?P<keyword>[^/]+)",
    )
    @extend_schema(
        summary="Elimina un keyword específico del resource",
        description="Elimina **solo la relación** entre el resource y el keyword indicado.",
        responses={204: None},
    )
    def delete_keyword(self, request, resource_pk=None, keyword=None):
        """
        Elimina la asociación de UN keyword específico del resource.
        No elimina el keyword global, solo la relación.
        """
        ds = self._get_resource(resource_pk)
        self._check_edit_perm(ds, request.user)

        ds.keywords.remove(keyword)
        return Response(status=204)
