# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Management command: carga las capas MGN INEGI (estados y municipios) a GeoNode
y las registra en IneiBaseLayer para el georeferenciador.

Uso:
    python manage.py load_inegi_base_layers \\
        --path /ruta/a/ejemplos/ \\
        --token Bearer_<JWT>

Los archivos esperados en --path:
    - mun22gw.zip  o  municipios.gpkg  (municipios)
    - dest22gw.zip o  estados.gpkg     (estados/entidades)

Si ya existe la capa en IneiBaseLayer se salta (usa --force para sobreescribir).
"""

import os
import zipfile

from django.core.management.base import BaseCommand

from sigic_geonode.sigic_data_importer.models import IneiBaseLayer


class Command(BaseCommand):
    help = "Carga capas MGN INEGI (estados/municipios) a GeoNode y las registra para georeferenciacion"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=".",
            help="Carpeta donde buscar los archivos MGN (ej. /ejemplos/)",
        )
        parser.add_argument(
            "--token",
            required=True,
            help="Token de autenticacion GeoNode (ej. 'Bearer eyJ...')",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Sobreescribe registros existentes en IneiBaseLayer",
        )

    def handle(self, *args, **options):
        import requests
        from django.conf import settings
        import tempfile
        import shutil

        path = options["path"]
        token = options["token"]
        force = options["force"]
        geonode_url = getattr(settings, "GEONODE_SERVER", "http://geonode/").rstrip("/")

        # Mapa de archivos esperados → config de capa
        layer_configs = [
            {
                "layer_type": "municipio",
                "candidates": ["mun22gw.zip", "municipios.gpkg", "municipios.zip"],
                "key_field": "CVE_GEO",
                "name_field": "NOM_MUN",
            },
            {
                "layer_type": "estado",
                "candidates": ["dest22gw.zip", "estados.gpkg", "estados.zip"],
                "key_field": "CVE_GEO",
                "name_field": "NOM_ENT",
            },
        ]

        for config in layer_configs:
            layer_type = config["layer_type"]

            if IneiBaseLayer.objects.filter(layer_type=layer_type).exists() and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Ya existe capa '{layer_type}'. Usa --force para sobreescribir."
                    )
                )
                continue

            file_to_upload = None
            for candidate in config["candidates"]:
                candidate_path = os.path.join(path, candidate)
                if os.path.exists(candidate_path):
                    file_to_upload = candidate_path
                    break

            if file_to_upload is None:
                self.stdout.write(
                    self.style.ERROR(
                        f"  No se encontro archivo para '{layer_type}' en {path}. "
                        f"Esperados: {config['candidates']}"
                    )
                )
                continue

            self.stdout.write(f"  Subiendo '{layer_type}' desde {file_to_upload}...")

            # Si es zip, extraer gpkg/shp para subir
            if file_to_upload.endswith(".zip"):
                tmpdir = tempfile.mkdtemp()
                try:
                    with zipfile.ZipFile(file_to_upload, "r") as zf:
                        zf.extractall(tmpdir)
                    # Buscar gpkg o shp dentro del zip
                    upload_path = None
                    for root, _, files in os.walk(tmpdir):
                        for fname in files:
                            if fname.endswith(".gpkg") or fname.endswith(".shp"):
                                upload_path = os.path.join(root, fname)
                                break
                        if upload_path:
                            break
                    if upload_path is None:
                        self.stdout.write(self.style.ERROR(f"  No se encontro .gpkg/.shp en {file_to_upload}"))
                        shutil.rmtree(tmpdir)
                        continue
                    dataset_id = self._upload_file(upload_path, token, geonode_url)
                finally:
                    shutil.rmtree(tmpdir)
            else:
                dataset_id = self._upload_file(file_to_upload, token, geonode_url)

            if dataset_id is None:
                continue

            IneiBaseLayer.objects.update_or_create(
                layer_type=layer_type,
                defaults={
                    "geonode_dataset_id": dataset_id,
                    "key_field": config["key_field"],
                    "name_field": config["name_field"],
                },
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Capa '{layer_type}' registrada correctamente (dataset {dataset_id})"
                )
            )

    def _upload_file(self, file_path: str, token: str, geonode_url: str):
        import time
        import requests

        filename = os.path.basename(file_path)
        upload_url = f"{geonode_url}/api/v2/uploads/upload/"

        with open(file_path, "rb") as f:
            resp = requests.post(
                upload_url,
                headers={"Authorization": token},
                files={"base_file": (filename, f)},
                data={"permissions": '{"users":{"AnonymousUser":["view_resourcebase"]}}'},
                timeout=300,
            )

        if not resp.ok:
            self.stdout.write(
                self.style.ERROR(f"  Upload fallido: {resp.status_code} {resp.text[:200]}")
            )
            return None

        data = resp.json()
        execution_id = data.get("execution_id") or data.get("id")
        if not execution_id:
            self.stdout.write(self.style.ERROR(f"  Sin execution_id: {data}"))
            return None

        # Polling
        status_url = f"{geonode_url}/api/v2/resource-service/execution-status/{execution_id}/"
        for attempt in range(30):
            time.sleep(5)
            r = requests.get(status_url, headers={"Authorization": token}, timeout=30)
            if r.ok:
                d = r.json()
                state = d.get("exec_status", "")
                if state == "finished":
                    resources = d.get("output_params", {}).get("resources", [])
                    if resources:
                        return resources[0].get("pk") or resources[0].get("id")
                elif state in ("failed", "error"):
                    self.stdout.write(self.style.ERROR(f"  Ejecucion fallida: {d}"))
                    return None
            self.stdout.write(f"    Esperando... ({attempt + 1}/30)")

        self.stdout.write(self.style.ERROR("  Timeout esperando GeoNode"))
        return None
