# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Tareas Celery para el importador de datos tabulares.

analyze_uploaded_file  → detecta esquema de columnas
import_tabular_to_geonode → convierte a GeoPackage y sube a GeoNode
"""

import logging
import os
import traceback

import requests
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

GEONODE_SERVER = getattr(settings, "GEONODE_SERVER", "http://django:8000/")


@shared_task(
    bind=True,
    name="sigic_data_importer.analyze_uploaded_file",
    queue="default",
    max_retries=2,
)
def analyze_uploaded_file(self, job_id: int):
    """Analiza el archivo subido y rellena column_schema del job."""
    from .models import DataImportJob
    from .file_reader import read_file_to_dataframe
    from .column_detector import detect_schema, suggest_geo_strategy

    try:
        job = DataImportJob.objects.get(pk=job_id)
        job.status = "analyzing"
        job.save(update_fields=["status"])

        file_path = job.file_path.path
        df = read_file_to_dataframe(file_path, job.file_format)

        schema = detect_schema(df)
        suggestion = suggest_geo_strategy(schema)

        job.column_schema = schema
        job.geo_strategy = suggestion["strategy"]
        job.geo_field_lat = suggestion.get("lat_field", "")
        job.geo_field_lon = suggestion.get("lon_field", "")
        job.geo_field_join = suggestion.get("join_field", "")
        job.status = "ready"
        job.save(update_fields=[
            "column_schema", "geo_strategy", "geo_field_lat",
            "geo_field_lon", "geo_field_join", "status",
        ])
        logger.info("Job %s analizado correctamente (%d columnas)", job_id, len(schema))

    except DataImportJob.DoesNotExist:
        logger.error("Job %s no encontrado", job_id)
    except Exception as exc:
        logger.error("Error analizando job %s: %s", job_id, traceback.format_exc())
        try:
            job = DataImportJob.objects.get(pk=job_id)
            job.status = "error"
            job.error_message = str(exc)
            job.save(update_fields=["status", "error_message"])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)


@shared_task(
    bind=True,
    name="sigic_data_importer.import_tabular_to_geonode",
    queue="default",
    max_retries=1,
    time_limit=600,
    soft_time_limit=540,
)
def import_tabular_to_geonode(self, job_id: int, authorization: str):
    """
    Convierte el DataFrame a GeoPackage (si hay estrategia geo) y lo sube a GeoNode.

    Para archivos sin geometria ('none') sube el CSV/Excel original como documento.
    """
    from .models import DataImportJob
    from .file_reader import read_file_to_dataframe
    from .geo_utils import build_geodataframe, export_to_geojson

    gpkg_path = None
    try:
        job = DataImportJob.objects.get(pk=job_id)
        job.status = "importing"
        job.save(update_fields=["status"])

        file_path = job.file_path.path
        df = read_file_to_dataframe(file_path, job.file_format)

        layer_name = job.original_filename.rsplit(".", 1)[0][:50]

        if job.geo_strategy != "none":
            gdf = build_geodataframe(
                df,
                geo_strategy=job.geo_strategy,
                geo_field_lat=job.geo_field_lat,
                geo_field_lon=job.geo_field_lon,
                geo_field_join=job.geo_field_join,
            )
            gpkg_path = export_to_geojson(gdf, layer_name)
            upload_file = gpkg_path
            upload_filename = f"{layer_name}.geojson"
            content_type = "application/geo+json"
        else:
            upload_file = file_path
            upload_filename = job.original_filename
            content_type = "text/csv"

        resolved_auth = _resolve_authorization(job, authorization)
        dataset_id = _upload_to_geonode(upload_file, upload_filename, content_type, resolved_auth)

        job.geonode_dataset_id = dataset_id
        job.status = "done"
        job.save(update_fields=["geonode_dataset_id", "status"])
        logger.info("Job %s importado correctamente → dataset %s", job_id, dataset_id)

    except Exception as exc:
        logger.error("Error importando job %s: %s", job_id, traceback.format_exc())
        try:
            job = DataImportJob.objects.get(pk=job_id)
            job.status = "error"
            job.error_message = str(exc)
            job.save(update_fields=["status", "error_message"])
        except Exception:
            pass
        raise
    finally:
        if gpkg_path and os.path.exists(gpkg_path):
            os.unlink(gpkg_path)


def _resolve_authorization(job, fallback: str) -> str:
    """
    Devuelve un header Authorization válido para las llamadas internas a GeoNode.

    Prefiere el Bearer JWT/OAuth2 que llegó con la request original.
    Si estaba vacío (sesión por cookies), busca el access token OAuth2 del
    usuario en la base de datos. Lanza ValueError si no hay ninguno disponible.
    """
    if fallback:
        return fallback

    from django.utils import timezone
    from oauth2_provider.models import AccessToken

    token = (
        AccessToken.objects
        .filter(user=job.owner, expires__gt=timezone.now())
        .order_by("-expires")
        .first()
    )
    if token:
        return f"Bearer {token.token}"

    raise ValueError(
        "No hay token OAuth2 activo para el usuario. "
        "Recarga la página e inicia sesión de nuevo antes de importar."
    )


def _upload_to_geonode(file_path: str, filename: str, content_type: str, authorization: str) -> int:
    """
    Sube un archivo a GeoNode via el importer y retorna el dataset_id.

    Usa el mismo flujo que pages/catalogo/cargar-archivos.vue.
    """
    upload_url = f"{GEONODE_SERVER.rstrip('/')}/api/v2/uploads/upload/"

    with open(file_path, "rb") as f:
        response = requests.post(
            upload_url,
            headers={"Authorization": authorization},
            files={"base_file": (filename, f, content_type)},
            data={"permissions": '{"users":{"AnonymousUser":["view_resourcebase"]}}'},
            timeout=300,
        )

    if not response.ok:
        raise RuntimeError(
            f"GeoNode upload fallido: {response.status_code} {response.text[:300]}"
        )

    data = response.json()
    # GeoNode importer retorna execution_id; esperamos el dataset_id resuelto
    # En esta version simplificada retornamos el execution_id como referencia
    # El job se actualiza con el dataset real una vez que GeoNode lo procesa
    execution_id = data.get("execution_id") or data.get("id")
    if not execution_id:
        raise RuntimeError(f"GeoNode no retorno execution_id: {data}")

    # Polling hasta resolver el dataset_id
    dataset_id = _poll_execution(execution_id, authorization)
    return dataset_id


def _poll_execution(execution_id, authorization: str, max_tries: int = 30) -> int:
    """Espera a que GeoNode resuelva el dataset_id del execution."""
    import time
    status_url = f"{GEONODE_SERVER.rstrip('/')}/api/v2/executionrequest/{execution_id}/"

    for _ in range(max_tries):
        r = requests.get(status_url, headers={"Authorization": authorization}, timeout=30)
        if r.ok:
            req = r.json().get("request", {})
            state = req.get("status", "")
            if state == "finished":
                # geonode_resource es el pk directo; resources[] es el fallback
                if req.get("geonode_resource"):
                    return req["geonode_resource"]
                resources = req.get("output_params", {}).get("resources", [])
                if resources:
                    return resources[0].get("id") or resources[0].get("pk")
            elif state in ("failed", "error"):
                raise RuntimeError(f"GeoNode execution fallida: {req}")
        time.sleep(5)

    raise RuntimeError(f"Timeout esperando ejecucion {execution_id}")
