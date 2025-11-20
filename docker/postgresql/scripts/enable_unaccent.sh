#!/bin/bash

# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

set -e

echo "==> Habilitando unaccent en GEONODE_DATABASE: $GEONODE_DATABASE"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$GEONODE_DATABASE" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS unaccent;
EOSQL

echo "==> Habilitando unaccent en GEONODE_GEODATABASE: $GEONODE_GEODATABASE"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$GEONODE_GEODATABASE" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS unaccent;
EOSQL

echo "==> unaccent habilitado en ambas bases."
