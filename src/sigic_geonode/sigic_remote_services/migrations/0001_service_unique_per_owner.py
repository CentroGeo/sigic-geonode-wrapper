# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Migración para modificar constraints de los modelos Service y Harvester de GeoNode.

Elimina los constraints unique globales y agrega constraints únicos compuestos
por owner para permitir que múltiples usuarios registren la misma URL de
servicio remoto.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("services", "24_initial"),
        ("harvesting", "0047_update_wms_harvester_type"),
    ]

    operations = [
        # =================================================================
        # Modificaciones a services_service
        # =================================================================
        # Eliminar constraint unique de base_url
        migrations.RunSQL(
            sql="ALTER TABLE services_service DROP CONSTRAINT IF EXISTS services_service_base_url_key;",
            reverse_sql="ALTER TABLE services_service ADD CONSTRAINT services_service_base_url_key UNIQUE (base_url);",
        ),
        # Eliminar constraint unique de name
        migrations.RunSQL(
            sql="ALTER TABLE services_service DROP CONSTRAINT IF EXISTS services_service_name_key;",
            reverse_sql="ALTER TABLE services_service ADD CONSTRAINT services_service_name_key UNIQUE (name);",
        ),
        # Agregar constraint único compuesto (base_url, owner_id)
        migrations.RunSQL(
            sql="ALTER TABLE services_service ADD CONSTRAINT services_service_base_url_owner_key UNIQUE (base_url, owner_id);",
            reverse_sql="ALTER TABLE services_service DROP CONSTRAINT IF EXISTS services_service_base_url_owner_key;",
        ),
        # Agregar constraint único compuesto (name, owner_id)
        migrations.RunSQL(
            sql="ALTER TABLE services_service ADD CONSTRAINT services_service_name_owner_key UNIQUE (name, owner_id);",
            reverse_sql="ALTER TABLE services_service DROP CONSTRAINT IF EXISTS services_service_name_owner_key;",
        ),
        # =================================================================
        # Modificaciones a harvesting_harvester
        # =================================================================
        # Eliminar constraint unique de name (definido como UniqueConstraint)
        migrations.RunSQL(
            sql='ALTER TABLE harvesting_harvester DROP CONSTRAINT IF EXISTS "unique name";',
            reverse_sql='ALTER TABLE harvesting_harvester ADD CONSTRAINT "unique name" UNIQUE (name);',
        ),
        # Agregar constraint único compuesto (name, default_owner_id)
        migrations.RunSQL(
            sql="ALTER TABLE harvesting_harvester ADD CONSTRAINT harvesting_harvester_name_owner_key UNIQUE (name, default_owner_id);",
            reverse_sql="ALTER TABLE harvesting_harvester DROP CONSTRAINT IF EXISTS harvesting_harvester_name_owner_key;",
        ),
    ]
