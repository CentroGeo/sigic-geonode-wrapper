# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Modelos para el importador de datos tabulares.

Flujo: DataImportJob guarda el estado a lo largo del wizard.
IneiBaseLayer registra las capas MGN precargadas para joins geograficos.
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class IneiBaseLayer(models.Model):
    """Capas MGN INEGI precargadas para georeferenciacion por clave o nombre."""

    LAYER_TYPES = [
        ("estado", "Estado"),
        ("municipio", "Municipio"),
    ]

    layer_type = models.CharField(max_length=20, choices=LAYER_TYPES, unique=True)
    # Nombre de la tabla en la BD geodata (cargada por data migration)
    table_name = models.CharField(
        max_length=100,
        default="",
        help_text="Nombre de tabla en PostGIS geodata (ej. inegi_estados)",
    )
    # Opcional: referencia al Dataset de GeoNode si se sube via importer
    geonode_dataset_id = models.IntegerField(
        verbose_name="ID del Dataset en GeoNode",
        null=True,
        blank=True,
    )
    key_field = models.CharField(
        max_length=100,
        help_text="Nombre del campo clave INEGI (ej. CVEGEO)",
    )
    name_field = models.CharField(
        max_length=100,
        help_text="Nombre del campo de nombre geografico (ej. NOMGEO)",
    )

    class Meta:
        db_table = "sigic_data_importer_inei_base_layer"

    def __str__(self):
        return f"MGN {self.get_layer_type_display()} (dataset {self.geonode_dataset_id})"


def _upload_path(instance, filename):
    return os.path.join("data_importer", str(instance.owner_id), filename)


class DataImportJob(models.Model):
    """Registro de un job de importacion de archivo tabular."""

    MAX_DRAFT_ITEMS = 999 if settings.DEBUG else 20

    DRAFT_STATUSES = (
        "pending",
        "analyzing",
        "ready",
        "importing",
        "done",
    )
    
    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("analyzing", "Analizando"),
        ("ready", "Listo para configurar"),
        ("importing", "Importando a GeoNode"),
        ("done", "Completado"),
        ("error", "Error"),
    ]

    GEO_STRATEGIES = [
        ("latlon", "Coordenadas lat/lon"),
        ("state_name", "Nombre de estado"),
        ("mun_name", "Nombre de municipio"),
        ("inegi_state_key", "Clave INEGI estado (2 digitos)"),
        ("inegi_mun_key", "Clave INEGI municipio (5 digitos)"),
        ("none", "Sin geometria"),
    ]

    FILE_FORMATS = [
        ("csv", "CSV"),
        ("xlsx", "Excel (.xlsx)"),
        ("xls", "Excel (.xls)"),
        ("json", "JSON"),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="data_import_jobs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, default="")

    original_filename = models.CharField(max_length=500)
    file_path = models.FileField(upload_to=_upload_path, max_length=500)
    file_format = models.CharField(max_length=10, choices=FILE_FORMATS)

    # Resultado del analisis automatico de columnas
    column_schema = models.JSONField(
        null=True,
        blank=True,
        help_text="Lista de {name, detected_type, confidence, sample_values, editable_type}",
    )

    # Estrategia geografica elegida por el usuario (o detectada)
    geo_strategy = models.CharField(
        max_length=30,
        choices=GEO_STRATEGIES,
        default="none",
    )
    geo_field_lat = models.CharField(max_length=200, blank=True, default="")
    geo_field_lon = models.CharField(max_length=200, blank=True, default="")
    geo_field_join = models.CharField(max_length=200, blank=True, default="")

    # Dataset de GeoNode creado al finalizar la importacion
    geonode_dataset_id = models.IntegerField(null=True, blank=True)

    # Site de tablero creado automaticamente
    dashboard_site_id = models.IntegerField(null=True, blank=True)

    # Metadatos de la capa (aplicados al dataset GeoNode tras la importacion)
    layer_abstract = models.TextField(blank=True, default="")
    layer_keywords = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Palabras clave separadas por coma",
    )
    layer_license = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Identificador de licencia (ej. CC-BY)",
    )
    layer_category = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Identificador de categoria topica GeoNode",
    )
    layer_attribution = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Fuente o propietario de los datos",
    )

    # Especificaciones de estilo elegidas por el usuario
    style_specs = models.JSONField(
        null=True, blank=True,
        help_text="Lista de {col, type, palette, n_classes, classification}",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sigic_data_importer_job"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.status})"
