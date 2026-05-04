# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

import re

import django.db.models.deletion
from django.db import migrations, models

_SUFFIX_RE = re.compile(r"_h\d+$")


def _strip_suffix(alternate):
    if not alternate:
        return alternate
    parts = alternate.split(":", 1)
    if len(parts) == 2:
        return f"{parts[0]}:{_SUFFIX_RE.sub('', parts[1])}"
    return _SUFFIX_RE.sub("", alternate)


def backfill_remote_typenames(apps, schema_editor):
    Dataset = apps.get_model("layers", "Dataset")
    RemoteLayerTypename = apps.get_model("sigic_remote_services", "RemoteLayerTypename")

    for dataset in Dataset.objects.filter(sourcetype="REMOTE").exclude(alternate=""):
        real_typename = _strip_suffix(dataset.alternate)
        if real_typename:
            RemoteLayerTypename.objects.update_or_create(
                dataset=dataset,
                defaults={"typename": real_typename},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_remote_services", "0001_service_unique_per_owner"),
        ("layers", "24_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RemoteLayerTypename",
            fields=[
                (
                    "dataset",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="remote_layer_typename",
                        serialize=False,
                        to="layers.dataset",
                    ),
                ),
                ("typename", models.CharField(max_length=512)),
            ],
            options={"app_label": "sigic_remote_services"},
        ),
        migrations.RunPython(backfill_remote_typenames, migrations.RunPython.noop),
    ]
