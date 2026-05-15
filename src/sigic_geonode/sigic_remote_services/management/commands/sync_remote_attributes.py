# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Management command: sincroniza atributos WFS para capas remotas existentes.

Llama a WFS DescribeFeatureType en el servidor de origen de cada dataset
remoto y persiste los atributos en la tabla Attribute de GeoNode.

Uso:
    python manage.py sync_remote_attributes
    python manage.py sync_remote_attributes --dataset-id 52
    python manage.py sync_remote_attributes --force
    python manage.py sync_remote_attributes --dry-run
"""

from django.core.management.base import BaseCommand

from geonode.layers.models import Dataset

from sigic_geonode.sigic_remote_services.wfs_attributes import sync_attributes_from_wfs


class Command(BaseCommand):
    help = "Sincroniza atributos WFS para datasets remotos que no los tienen"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-id",
            type=int,
            default=None,
            metavar="ID",
            help="Sincronizar solo el dataset con este pk",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Re-sincronizar aunque el dataset ya tenga atributos",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Mostrar qué se sincronizaría sin escribir en la base de datos",
        )

    def handle(self, *args, **options):
        dataset_id = options["dataset_id"]
        force = options["force"]
        dry_run = options["dry_run"]

        qs = Dataset.objects.filter(sourcetype="REMOTE")
        if dataset_id is not None:
            qs = qs.filter(pk=dataset_id)

        total = qs.count()
        self.stdout.write(
            f"Datasets remotos a procesar: {total}"
            + (" [dry-run]" if dry_run else "")
        )

        ok = 0
        skipped = 0
        failed = 0

        for dataset in qs.iterator():
            label = f"  [{dataset.pk}] {dataset.title or dataset.name}"

            if not force and dataset.attribute_set.exists():
                self.stdout.write(f"{label} — omitido (ya tiene atributos)")
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"{label} — se sincronizaría")
                ok += 1
                continue

            try:
                synced = sync_attributes_from_wfs(dataset, force=force)
                if synced:
                    self.stdout.write(
                        self.style.SUCCESS(f"{label} — {synced} atributos sincronizados")
                    )
                    ok += 1
                else:
                    self.stdout.write(f"{label} — sin atributos obtenidos desde WFS")
                    skipped += 1
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"{label} — ERROR: {exc}"))
                failed += 1

        self.stdout.write(
            f"\nResumen: {ok} sincronizados, {skipped} omitidos, {failed} con error"
        )
