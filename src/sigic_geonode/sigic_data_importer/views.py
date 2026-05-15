# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
ViewSet para el importador de datos tabulares.

Endpoints:
  POST   /api/v2/data-importer/upload/              → sube archivo, crea job
  GET    /api/v2/data-importer/jobs/{id}/           → estado del job
  PATCH  /api/v2/data-importer/jobs/{id}/schema/    → corrige tipos/estrategia
  POST   /api/v2/data-importer/jobs/{id}/geo-preview/ → preview GeoJSON
  POST   /api/v2/data-importer/jobs/{id}/import/    → importa a GeoNode
  POST   /api/v2/data-importer/jobs/{id}/create-tablero/ → crea tablero
"""

import logging

from rest_framework import permissions, status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

from .models import DataImportJob
from .serializers import (
    CreateTableroSerializer,
    DataImportJobSerializer,
    GeoPreviewSerializer,
    SchemaUpdateSerializer,
)

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

AUTHENTICATION_CLASSES = [
    BasicAuthentication,
    SessionAuthentication,
    OAuth2Authentication,
    KeycloakJWTAuthentication,
]


class DataImporterViewSet(GenericViewSet):
    """Wizard de importacion de datos tabulares a tableros de datos."""

    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataImportJobSerializer

    def get_queryset(self):
        return DataImportJob.objects.filter(owner=self.request.user)

    # ------------------------------------------------------------------
    # POST /api/v2/data-importer/upload/
    # ------------------------------------------------------------------
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "Se requiere el campo 'file'."}, status=400)

        ext = file_obj.name.rsplit(".", 1)[-1].lower() if "." in file_obj.name else ""
        if ext not in _ALLOWED_EXTENSIONS:
            return Response(
                {"detail": f"Formato no soportado. Use: {', '.join(_ALLOWED_EXTENSIONS)}."},
                status=400,
            )

        if file_obj.size > _MAX_FILE_SIZE:
            return Response({"detail": "Archivo demasiado grande (max 50 MB)."}, status=400)

        job = DataImportJob.objects.create(
            owner=request.user,
            original_filename=file_obj.name,
            file_path=file_obj,
            file_format=ext,
            status="pending",
        )

        from .tasks import analyze_uploaded_file
        analyze_uploaded_file.delay(job.id)

        return Response(DataImportJobSerializer(job).data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # GET /api/v2/data-importer/jobs/{id}/
    # ------------------------------------------------------------------
    def retrieve(self, request, pk=None):
        job = self._get_job(pk)
        if job is None:
            return Response({"detail": "No encontrado."}, status=404)
        return Response(DataImportJobSerializer(job).data)

    # ------------------------------------------------------------------
    # PATCH /api/v2/data-importer/jobs/{id}/schema/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["patch"], url_path="schema")
    def update_schema(self, request, pk=None):
        job = self._get_job(pk)
        if job is None:
            return Response({"detail": "No encontrado."}, status=404)

        ser = SchemaUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        if "column_schema" in d:
            job.column_schema = d["column_schema"]
        if "geo_strategy" in d:
            job.geo_strategy = d["geo_strategy"]
        if "geo_field_lat" in d:
            job.geo_field_lat = d["geo_field_lat"]
        if "geo_field_lon" in d:
            job.geo_field_lon = d["geo_field_lon"]
        if "geo_field_join" in d:
            job.geo_field_join = d["geo_field_join"]

        job.save(update_fields=[
            "column_schema", "geo_strategy",
            "geo_field_lat", "geo_field_lon", "geo_field_join",
        ])
        return Response(DataImportJobSerializer(job).data)

    # ------------------------------------------------------------------
    # POST /api/v2/data-importer/jobs/{id}/geo-preview/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="geo-preview")
    def geo_preview(self, request, pk=None):
        job = self._get_job(pk)
        if job is None:
            return Response({"detail": "No encontrado."}, status=404)

        ser = GeoPreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        import traceback as _tb
        from .file_reader import read_file_to_dataframe
        from .geo_utils import geo_preview as compute_preview

        try:
            df = read_file_to_dataframe(job.file_path.path, job.file_format)
            result = compute_preview(
                df,
                geo_strategy=d["geo_strategy"],
                geo_field_lat=d.get("geo_field_lat", ""),
                geo_field_lon=d.get("geo_field_lon", ""),
                geo_field_join=d.get("geo_field_join", ""),
            )
            return Response(result)
        except Exception as exc:
            return Response({"ok": False, "error": str(exc), "traceback": _tb.format_exc()}, status=400)

    # ------------------------------------------------------------------
    # POST /api/v2/data-importer/jobs/{id}/import/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="import")
    def import_to_geonode(self, request, pk=None):
        job = self._get_job(pk)
        if job is None:
            return Response({"detail": "No encontrado."}, status=404)
        if job.status not in ("ready", "error"):
            return Response(
                {"detail": f"El job esta en estado '{job.status}'. Debe estar 'ready'."},
                status=400,
            )

        authorization = request.META.get("HTTP_AUTHORIZATION", "")

        from .tasks import import_tabular_to_geonode
        import_tabular_to_geonode.delay(job.id, authorization)

        job.status = "importing"
        job.save(update_fields=["status"])
        return Response({"detail": "Importacion iniciada.", "job_id": job.id})

    # ------------------------------------------------------------------
    # POST /api/v2/data-importer/jobs/{id}/create-tablero/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="create-tablero")
    def create_tablero(self, request, pk=None):
        job = self._get_job(pk)
        if job is None:
            return Response({"detail": "No encontrado."}, status=404)

        ser = CreateTableroSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # Persistir nombre y metadatos en el job
        update_fields = []
        if d.get("name"):
            job.original_filename = d["name"]
            update_fields.append("original_filename")

        for field in ("layer_abstract", "layer_keywords", "layer_license",
                      "layer_category", "layer_attribution"):
            if d.get(field) is not None:
                setattr(job, field, d[field])
                update_fields.append(field)

        if d.get("style_specs") is not None:
            job.style_specs = d["style_specs"]
            update_fields.append("style_specs")

        if update_fields:
            job.save(update_fields=update_fields)

        # Aplicar metadatos al dataset de GeoNode
        if job.geonode_dataset_id:
            _apply_metadata_to_dataset(job, d.get("name", ""), d.get("description", "") or d.get("layer_abstract", ""))

        # Generar estilos con las preferencias del usuario
        if job.geonode_dataset_id and job.style_specs and job.geo_strategy != "none":
            try:
                from geonode.layers.models import Dataset
                from sigic_geonode.sigic_georeference.style_generator import (
                    generate_and_register_styles_with_specs,
                )
                ds = Dataset.objects.filter(id=job.geonode_dataset_id).first()
                if ds:
                    generate_and_register_styles_with_specs(
                        ds, job.style_specs,
                        default_col=d.get("default_style_col") or None,
                    )
            except Exception:
                logger.exception("Style generation failed for job %s (non-fatal)", pk)

        from .tablero_builder import build_tablero_from_job
        try:
            site_id = build_tablero_from_job(job)
            job.dashboard_site_id = site_id
            job.save(update_fields=["dashboard_site_id"])
            return Response({"site_id": site_id})
        except Exception as exc:
            logger.exception("Error creando tablero para job %s", pk)
            return Response({"detail": str(exc)}, status=500)

    # ------------------------------------------------------------------
    # POST /api/v2/data-importer/jobs/{id}/finalize-layer/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="finalize-layer")
    def finalize_layer(self, request, pk=None):
        job = self._get_job(pk)
        if job is None:
            return Response({"detail": "No encontrado."}, status=404)
        if not job.geonode_dataset_id:
            return Response(
                {"detail": "El job no tiene un dataset de GeoNode asociado. Ejecuta 'import' primero."},
                status=400,
            )

        d = request.data
        update_fields = []

        if d.get("name"):
            job.original_filename = d["name"]
            update_fields.append("original_filename")

        for field in ("layer_abstract", "layer_keywords", "layer_license",
                      "layer_category", "layer_attribution"):
            if d.get(field) is not None:
                setattr(job, field, d[field])
                update_fields.append(field)

        if d.get("style_specs") is not None:
            job.style_specs = d["style_specs"]
            update_fields.append("style_specs")

        if update_fields:
            job.save(update_fields=update_fields)

        _apply_metadata_to_dataset(
            job,
            d.get("name", "") or job.original_filename,
            d.get("layer_abstract", ""),
        )

        if job.geonode_dataset_id and job.style_specs and job.geo_strategy != "none":
            try:
                from geonode.layers.models import Dataset
                from sigic_geonode.sigic_georeference.style_generator import (
                    generate_and_register_styles_with_specs,
                )
                ds = Dataset.objects.filter(id=job.geonode_dataset_id).first()
                if ds:
                    generate_and_register_styles_with_specs(
                        ds, job.style_specs,
                        default_col=d.get("default_style_col") or None,
                    )
            except Exception:
                logger.exception("Style generation failed for job %s (non-fatal)", pk)

        try:
            from geonode.layers.models import Dataset
            ds = Dataset.objects.filter(id=job.geonode_dataset_id).first()
            alternate = ds.alternate if ds else None
        except Exception:
            alternate = None

        return Response({
            "dataset_id": job.geonode_dataset_id,
            "alternate": alternate,
        })

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _get_job(self, pk):
        return DataImportJob.objects.filter(pk=pk, owner=self.request.user).first()


def _apply_metadata_to_dataset(job, title: str, abstract: str) -> None:
    """Aplica metadatos del job al ResourceBase de GeoNode via ORM."""
    try:
        from django.db.models import Q
        from geonode.base.models import ResourceBase, TopicCategory

        resource = ResourceBase.objects.filter(id=job.geonode_dataset_id).first()
        if resource is None:
            return

        update_fields = []
        if title:
            resource.title = title
            update_fields.append("title")
        if abstract:
            resource.abstract = abstract
            update_fields.append("abstract")
        if job.layer_attribution:
            resource.attribution = job.layer_attribution
            update_fields.append("attribution")
        if update_fields:
            resource.save(update_fields=update_fields)

        if job.layer_category:
            cat = TopicCategory.objects.filter(identifier=job.layer_category).first()
            if cat:
                resource.category = cat
                resource.save(update_fields=["category"])

        if job.layer_license:
            try:
                from geonode.base.models import License
                lic = License.objects.filter(
                    Q(identifier=job.layer_license) | Q(abbreviation=job.layer_license)
                ).first()
                if lic:
                    resource.license = lic
                    resource.save(update_fields=["license"])
            except Exception:
                pass

        if job.layer_keywords:
            keywords = [k.strip() for k in job.layer_keywords.split(",") if k.strip()]
            if keywords:
                resource.keywords.add(*keywords)

    except Exception:
        logger.exception("Error aplicando metadatos a dataset %s", job.geonode_dataset_id)




class CategoriesView(APIView):
    """
    GET /api/v2/data-importer/categories/
    Devuelve las categorias tematicas de GeoNode con gn_description traducida
    al idioma activo del servidor (es por defecto en SIGIC).
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        from django.utils.translation import gettext, override
        from geonode.base.models import TopicCategory

        cats = TopicCategory.objects.filter(is_choice=True).order_by("gn_description")
        lang = request.GET.get("lang", "es")
        with override(lang):
            data = [
                {
                    "id": c.id,
                    "identifier": c.identifier,
                    "gn_description": gettext(c.gn_description),
                    "fa_class": c.fa_class,
                }
                for c in cats
                if c.gn_description
            ]
        return Response(data)
