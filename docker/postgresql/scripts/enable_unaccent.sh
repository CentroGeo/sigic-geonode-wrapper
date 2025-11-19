#!/bin/bash
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
