# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_dashboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="indicator",
            name="general_values",
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name="Valores generales agregados para cuadros KPI",
            ),
        ),
    ]
