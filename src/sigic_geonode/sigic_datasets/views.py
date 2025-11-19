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

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from geonode.layers.models import Dataset
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

    def get_dataset(self, pk):
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
        ds = self.get_dataset(dataset_pk)
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
        ds = self.get_dataset(dataset_pk)

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
        ds = self.get_dataset(dataset_pk)
        ds.keywords.set(request.data)
        return Response(list(ds.keywords.names()))

    @extend_schema(
        summary="Elimina la asociación con keywords del dataset",
        description="No elimina los keywords globales, solo la relación.",
        request={"application/json": {"type": "array", "items": {"type": "string"}}},
        responses={
            200: {"application/json": {"type": "array", "items": {"type": "string"}}}
        },
    )
    def destroy(self, request, dataset_pk=None):
        """
        Elimina la asociación entre el dataset y los keywords indicados.

        Importante:
            - No elimina los keywords globales.
            - Solo elimina la relación con este dataset.

        Returns:
            Response: Lista actualizada de keywords.
        """
        ds = self.get_dataset(dataset_pk)

        for kw in request.data:
            ds.keywords.remove(kw)

        return Response(list(ds.keywords.names()))
