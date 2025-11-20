# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from geonode.layers.models import Dataset
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class DatasetKeywordsViewSet(ViewSet):
    """
    Gestiona los *keywords* (etiquetas) asociados a un Dataset de GeoNode.

    Este ViewSet proporciona un endpoint estable y desacoplado del
    serializador interno de GeoNode. Permite consultar, agregar, reemplazar
    o eliminar *keywords* sin pasar por DynamicRest ni por el
    ResourceBaseSerializer, evitando errores de parseo y problemas en PATCH.

    Endpoints soportados:

    - **GET /api/v2/datasets/{dataset_pk}/keywords/**
        Devuelve la lista actual de keywords asociados al dataset.

    - **POST /api/v2/datasets/{dataset_pk}/keywords/**
        Agrega nuevos keywords al dataset. Los existentes se preservan.
        Los keywords inexistentes se crean automáticamente.

    - **PUT /api/v2/datasets/{dataset_pk}/keywords/**
        Reemplaza completamente el conjunto de keywords del dataset por los
        proporcionados en el cuerpo de la petición.

    - **DELETE /api/v2/datasets/{dataset_pk}/keywords/**
        Elimina la asociación entre el dataset y los keywords indicados.
        No elimina los keywords del catálogo global, solo la relación.

    Notas:
        - Requiere autenticación.
        - El cuerpo de las peticiones debe ser SIEMPRE una lista JSON
          de cadenas, por ejemplo:
              ["bosque", "eudr", "mexico"]
        - Se basa en Taggit: los keywords se crean automáticamente si no existen.
        - No modifica vocabularios ni tesauros; únicamente relaciones del dataset.
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def _get_dataset(self, pk):
        """
        Obtiene el Dataset solicitado o lanza HTTP 404.

        Args:
            pk (int): ID del Dataset.

        Returns:
            Dataset: Instancia del dataset solicitado.

        Raises:
            Http404: Si no existe el dataset.
        """
        return get_object_or_404(Dataset, pk=pk)

    def _check_view_perm(self, dataset, user):
        """
        Verifica si un usuario tiene permiso para *ver* el dataset.

        Reglas aplicadas
        ----------------
        1. Si el dataset está publicado **y** aprobado (`is_published` + `is_approved`),
           el acceso es público y se permite a cualquier usuario, autenticado o no.

        2. Si el usuario está autenticado, se le permite el acceso únicamente si
           posee el permiso `base.view_resourcebase` sobre el `resourcebase_ptr`
           del dataset.

        3. Si ninguna condición se cumple, se lanza `PermissionDenied`.

        Parámetros
        ----------
        dataset : Dataset
            El dataset cuyo acceso se está validando.

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
        if dataset.is_published and dataset.is_approved:
            return

        # Caso 2: usuario autenticado con permiso de lectura
        if user and user.is_authenticated:
            if user.has_perm("base.view_resourcebase", dataset.resourcebase_ptr):
                return

        raise PermissionDenied("You do not have permission to view this dataset.")

    def _check_edit_perm(self, dataset, user):
        """
        Verifica si un usuario tiene permisos para modificar estilos del dataset.

        Reglas aplicadas
        ----------------
        1. El usuario debe estar autenticado.
           Si no lo está, se lanza inmediatamente `PermissionDenied`.

        2. Si el usuario es `superuser`, se permite la edición sin más validaciones.

        3. Para usuarios normales, solo se permite continuar si tienen el permiso
           `base.change_layer_style` sobre el `resourcebase_ptr` del dataset.

        Si ninguna condición se cumple, se lanza `PermissionDenied`.

        Parámetros
        ----------
        dataset : Dataset
            El dataset cuyo permiso de edición se está evaluando.

        user : User
            Usuario autenticado que realiza la solicitud.

        Excepciones
        -----------
        PermissionDenied
            Cuando el usuario no posee los permisos requeridos.

        Notas
        -----
        - Este método define *quién puede modificar estilos SLD*, de forma coherente
          con los permisos de GeoNode.
        - Se usa en `create`, `update` y `destroy` de estilos SLD.
        """

        if not (user and user.is_authenticated):
            raise PermissionDenied("Authentication required.")

        # superuser → acceso total
        if user.is_superuser:
            return

        if user.has_perm("base.change_layer_style", dataset.resourcebase_ptr):
            return

        raise PermissionDenied("You do not have permission to modify styles.")

    @extend_schema(
        summary="Obtiene los keywords del dataset",
        responses={
            200: {"application/json": {"type": "array", "items": {"type": "string"}}}
        },
        description="Devuelve la lista de keywords asociados al dataset.",
    )
    def list(self, request, dataset_pk=None):
        """
        Lista todos los keywords asociados al dataset.

        Returns:
            Response: Lista JSON con los nombres de los keywords.
        """
        ds = self._get_dataset(dataset_pk)
        return Response(list(ds.keywords.names()))

    @extend_schema(
        summary="Agrega keywords al dataset",
        request={"application/json": {"type": "array", "items": {"type": "string"}}},
        responses={
            200: {"application/json": {"type": "array", "items": {"type": "string"}}}
        },
        examples=[OpenApiExample("Agregar etiquetas", value=["bosque", "eudr"])],
    )
    def create(self, request, dataset_pk=None):
        """
        Agrega uno o varios keywords al dataset sin eliminar los existentes.

        El cuerpo debe ser una lista JSON de cadenas.
        Los keywords inexistentes se crean automáticamente.

        Returns:
            Response: Lista actualizada de keywords.
        """
        ds = self._get_dataset(dataset_pk)
        self._check_edit_perm(ds, request.user)

        for kw in request.data:
            ds.keywords.add(kw)

        return Response(list(ds.keywords.names()))

    @extend_schema(
        summary="Reemplaza todos los keywords del dataset",
        description="Sobrescribe completamente el conjunto de keywords.",
        request={"application/json": {"type": "array", "items": {"type": "string"}}},
        responses={
            200: {"application/json": {"type": "array", "items": {"type": "string"}}}
        },
    )
    def update(self, request, dataset_pk=None):
        """
        Reemplaza todos los keywords del dataset por los proporcionados.

        Equivalente a llamar a:
            dataset.keywords.set(lista)

        Returns:
            Response: Lista actualizada de keywords.
        """
        ds = self._get_dataset(dataset_pk)
        self._check_edit_perm(ds, request.user)

        ds.keywords.set(request.data)
        return Response(list(ds.keywords.names()))

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"(?P<keyword>[^/]+)",
    )
    @extend_schema(
        summary="Elimina un keyword específico del dataset",
        description="Elimina **solo la relación** entre el dataset y el keyword indicado.",
        responses={204: None},
    )
    def delete_keyword(self, request, dataset_pk=None, keyword=None):
        """
        Elimina la asociación de UN keyword específico del dataset.
        No elimina el keyword global, solo la relación.
        """
        ds = self._get_dataset(dataset_pk)
        self._check_edit_perm(ds, request.user)

        ds.keywords.remove(keyword)

        return Response(status=204)
