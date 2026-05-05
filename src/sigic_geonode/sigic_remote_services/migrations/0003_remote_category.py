# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Crea la categoría temática especial 'externalCatalog' para recursos cosechados
de servicios remotos, usada como categoría por defecto hasta que el usuario
asigne la categoría definitiva en los metadatos.
"""

from django.db import migrations


def create_external_catalog_category(apps, schema_editor):
    TopicCategory = apps.get_model("base", "TopicCategory")
    TopicCategory.objects.get_or_create(
        identifier="externalCatalog",
        defaults={
            "gn_description": "Catálogo externo",
            "description": "Recursos cosechados de servicios remotos externos",
            "is_choice": True,
            "fa_class": "fa-cloud-download",
        },
    )


def remove_external_catalog_category(apps, schema_editor):
    TopicCategory = apps.get_model("base", "TopicCategory")
    TopicCategory.objects.filter(identifier="externalCatalog").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_remote_services", "0002_remote_layer_typename"),
        ("base", "24_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_external_catalog_category,
            remove_external_catalog_category,
        ),
    ]
