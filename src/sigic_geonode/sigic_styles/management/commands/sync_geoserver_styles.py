# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

"""
Management command: sincroniza estilos de GeoServer que no tienen registro en GeoNode.

Para cada dataset local, consulta GeoServer para obtener todos los estilos
asociados al layer. Si un estilo existe en GeoServer pero no tiene objeto Style
en la base de datos de GeoNode, descarga el SLD y crea el registro.

Uso:
    python manage.py sync_geoserver_styles
    python manage.py sync_geoserver_styles --dataset-pk 42
    python manage.py sync_geoserver_styles --dry-run
"""

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from geonode.layers.models import Dataset, Style as GNStyle


class Command(BaseCommand):
    help = "Sincroniza estilos de GeoServer que no tienen registro en GeoNode"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-pk",
            type=int,
            default=None,
            metavar="PK",
            help="Sincronizar solo el dataset con este pk",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Mostrar qué se sincronizaría sin escribir en la base de datos",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        dataset_pk = options["dataset_pk"]

        gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
        auth = (
            settings.OGC_SERVER["default"]["USER"],
            settings.OGC_SERVER["default"]["PASSWORD"],
        )

        qs = Dataset.objects.filter(sourcetype="LOCAL")
        if dataset_pk:
            qs = qs.filter(pk=dataset_pk)

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No se encontraron datasets para procesar."))
            return

        total_synced = 0
        total_already = 0
        total_errors = 0

        for dataset in qs:
            layer_name = dataset.alternate
            if not layer_name:
                continue

            workspace = layer_name.split(":")[0]

            try:
                style_names = self._get_layer_style_names(gs_url, auth, layer_name)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  [{dataset.pk}] {dataset.title}: error al consultar GeoServer — {e}")
                )
                continue

            if not style_names:
                continue

            existing = set(
                GNStyle.objects.filter(name__in=style_names).values_list("name", flat=True)
            )

            new_styles = style_names - existing
            if not new_styles and not dry_run:
                # Garantizar asociaciones para los ya existentes
                for style in GNStyle.objects.filter(name__in=existing):
                    dataset.styles.add(style)
                total_already += len(existing)
                continue

            for style_name in new_styles:
                self.stdout.write(f"  [{dataset.pk}] {style_name} → ", ending="")

                if dry_run:
                    self.stdout.write(self.style.WARNING("(dry-run)"))
                    total_synced += 1
                    continue

                url_sld = f"{gs_url}/rest/workspaces/{workspace}/styles/{style_name}.sld"
                r_sld = requests.get(url_sld, auth=auth)

                if r_sld.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"error HTTP {r_sld.status_code}"))
                    total_errors += 1
                    continue

                style = GNStyle(
                    name=style_name,
                    sld_title=style_name,
                    workspace=workspace,
                    sld_body=r_sld.text,
                    sld_version="1.0.0",
                    sld_url=url_sld,
                )
                style.save()
                dataset.styles.add(style)
                self.stdout.write(self.style.SUCCESS("sincronizado"))
                total_synced += 1

            total_already += len(existing)

        label = "(dry-run) " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{label}Resultado: {total_synced} sincronizados, "
                f"{total_already} ya registrados, {total_errors} errores."
            )
        )

    def _get_layer_style_names(self, gs_url, auth, layer_name):
        style_items = []
        r = requests.get(f"{gs_url}/rest/layers/{layer_name}/styles.json", auth=auth)
        r.raise_for_status()
        raw = r.json().get("styles", {}).get("style", [])
        if isinstance(raw, dict):
            style_items = [raw]
        elif isinstance(raw, list):
            style_items = raw

        names = {s.get("name") for s in style_items if isinstance(s, dict)}

        r2 = requests.get(f"{gs_url}/rest/layers/{layer_name}.json", auth=auth)
        r2.raise_for_status()
        default_raw = (
            r2.json().get("layer", {}).get("defaultStyle", {}).get("name", "")
        )
        if ":" in default_raw:
            default_raw = default_raw.split(":")[-1]
        if default_raw:
            names.add(default_raw)

        return names
