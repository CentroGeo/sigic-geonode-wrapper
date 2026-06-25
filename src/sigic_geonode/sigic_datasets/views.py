# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from geonode.layers.models import Dataset
from rest_framework import status as drf_status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .metadata_import import detect_format, parse_dublin_core, parse_fgdc, parse_iso19139


class SigicDatasetMetadataImportViewSet(ViewSet):
    """
    Importa metadatos desde un archivo XML estándar (ISO 19139 o Dublin Core)
    y retorna los campos parseados para pre-llenar el formulario del frontend.

    No escribe nada en la base de datos — solo parsea y devuelve JSON.
    """

    permission_classes = [IsAuthenticated]

    def _get_dataset_or_404(self, dataset_pk):
        try:
            return Dataset.objects.get(pk=dataset_pk)
        except Dataset.DoesNotExist:
            raise NotFound("Dataset not found")

    def _check_edit_perm(self, dataset, user):
        if not user or not user.is_authenticated:
            raise PermissionDenied("Autenticación requerida.")
        if user.is_superuser:
            return
        if user.has_perm("base.change_resourcebase", dataset.resourcebase_ptr):
            return
        if dataset.owner == user:
            return
        raise PermissionDenied("No tienes permiso para editar este dataset.")

    def create(self, request, dataset_pk=None):
        """
        POST /api/v2/datasets/{pk}/metadata-import/

        Body: multipart/form-data con campo 'xml_file' (archivo .xml)

        Respuesta:
        {
            "format": "iso19139" | "dublin_core",
            "fields": { <campo_store>: <valor>, ... }
        }
        """
        dataset = self._get_dataset_or_404(dataset_pk)
        self._check_edit_perm(dataset, request.user)

        xml_file = request.FILES.get("xml_file")
        if not xml_file:
            return Response(
                {"error": "Falta el archivo 'xml_file' en el body."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        xml_bytes = xml_file.read()
        fmt = detect_format(xml_bytes)

        if fmt == "unknown":
            return Response(
                {
                    "error": (
                        "No se reconoció el formato del archivo XML. "
                        "Se esperaba ISO 19139, Dublin Core o FGDC."
                    )
                },
                status=drf_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        _parsers = {
            "iso19139": parse_iso19139,
            "dublin_core": parse_dublin_core,
            "fgdc": parse_fgdc,
        }
        try:
            fields = _parsers[fmt](xml_bytes)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        return Response({"format": fmt, "fields": fields})
