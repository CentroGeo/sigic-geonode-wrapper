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

echo "==> Habilitando sigic_geonode_geoweb: $GEONODE_DATABASE"

if [ "$USE_IDEGEOWEB" = "True" ]; then
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$GEONODE_DATABASE" <<-EOSQL
    CREATE DATABASE sigic_geonode_geoweb;
EOSQL
fi

echo "==> sigic_geonode_geoweb habilitado"