from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import SLDUploadSerializer
from .utils import (
    delete_style,
    list_styles,
    set_default_style,
    sync_sld_with_geonode,
    upload_sld_to_geoserver,
)


class SLDViewSet(viewsets.ViewSet):
    """
    ViewSet para gestionar estilos SLD asociados a datasets.
    Permite subir, listar y (en el futuro) eliminar estilos.
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """
        Sube un estilo SLD (archivo o texto) y lo asocia al dataset.
        """
        serializer = SLDUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset_name = serializer.validated_data["dataset_name"]
        sld_file = serializer.validated_data.get("sld_file")
        sld_body = serializer.validated_data.get("sld_body")
        is_default = serializer.validated_data.get("is_default", False)

        if sld_file:
            sld_body = sld_file.read().decode("utf-8")

        sld_name = f"{dataset_name}_custom_{request.user.username}"

        # Subir a GeoServer
        sld_url = upload_sld_to_geoserver(dataset_name, sld_name, sld_body, is_default)

        # Sincronizar con GeoNode
        style = sync_sld_with_geonode(dataset_name, sld_name, sld_url, is_default)

        return Response(
            {
                "message": "Estilo SLD cargado correctamente",
                "dataset": dataset_name,
                "style": style.name,
                "sld_url": sld_url,
                "is_default": style.is_default,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="style_list")
    def style_list(self, request, pk=None):
        """
        Lista todos los estilos registrados para un dataset.
        El parámetro <pk> es el nombre del dataset.
        """
        try:
            styles = list_styles(pk)
            return Response(
                {"dataset": pk, "styles": styles},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True, methods=["post"], url_path="set-default/(?P<style_name>[^/.]+)"
    )
    def set_default(self, request, pk=None, style_name=None):
        """
        Marca un estilo como predeterminado en GeoServer y GeoNode.
        """
        try:
            style = set_default_style(pk, style_name)
            return Response(
                {
                    "message": f"El estilo '{style_name}' ahora es el predeterminado para '{pk}'.",
                    "dataset": pk,
                    "style": style.name,
                    "sld_url": style.sld_url,
                    "is_default": style.is_default,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"], url_path="delete/(?P<style_name>[^/.]+)")
    def delete(self, request, pk=None, style_name=None):
        """
        Elimina un estilo SLD tanto en GeoServer como en GeoNode.
        """
        try:
            delete_style(pk, style_name)
            return Response(
                {
                    "message": f"Estilo '{style_name}' eliminado correctamente del dataset '{pk}'"
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
