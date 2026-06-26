# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2026)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from django.db import migrations

NEW_CATEGORIES = [
    {
        "identifier": "medioAmbienteRecursosNaturales",
        "gn_description": "Medio ambiente y recursos naturales",
        "description": "Medio ambiente y recursos naturales",
        "is_choice": True,
        "fa_class": "fa-leaf",
    },
    {
        "identifier": "infraestructuraServiciosUrbanosRegionales",
        "gn_description": "Infraestructura y servicios urbanos regionales",
        "description": "Infraestructura y servicios urbanos regionales",
        "is_choice": True,
        "fa_class": "fa-building-o",
    },
    {
        "identifier": "territorioLimitesCatastro",
        "gn_description": "Territorio, límites y catastro",
        "description": "Territorio, límites y catastro",
        "is_choice": True,
        "fa_class": "fa-map-o",
    },
    {
        "identifier": "sociedadDemografiaEconomia",
        "gn_description": "Sociedad, demografía y economía",
        "description": "Sociedad, demografía y economía",
        "is_choice": True,
        "fa_class": "fa-users",
    },
    {
        "identifier": "sensoresRemotosMapasBase",
        "gn_description": "Sensores remotos y mapas base",
        "description": "Sensores remotos y mapas base",
        "is_choice": True,
        "fa_class": "fa-globe",
    },
]


def create_new_categories(apps, schema_editor):
    TopicCategory = apps.get_model("base", "TopicCategory")
    for category in NEW_CATEGORIES:
        TopicCategory.objects.update_or_create(
            identifier=category["identifier"],
            defaults={
                "gn_description": category["gn_description"],
                "description": category["description"],
                "gn_description_en": category["gn_description"],
                "description_en": category["description"],
                "is_choice": category["is_choice"],
                "fa_class": category["fa_class"],
            },
        )


def remove_new_categories(apps, schema_editor):
    TopicCategory = apps.get_model("base", "TopicCategory")
    identifiers = [category["identifier"] for category in NEW_CATEGORIES]
    TopicCategory.objects.filter(identifier__in=identifiers).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_remote_services", "0004_add_categories"),
        ("base", "24_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_new_categories,
            remove_new_categories,
        ),
    ]
