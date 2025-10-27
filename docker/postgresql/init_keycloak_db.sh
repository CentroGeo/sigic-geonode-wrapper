#!/bin/bash
set -e

echo "🔍 Verificando base de datos Keycloak..."

if [ "${ENABLE_KEYCLOAK_PROXY}" != "True" ]; then
  echo "🟡 ENABLE_KEYCLOAK_PROXY=False, no se creará la base."
  exit 0
fi

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"

# Esperar hasta que el puerto esté disponible
until (echo > /dev/tcp/$DB_HOST/$DB_PORT) >/dev/null 2>&1; do
  echo "⏳ Esperando a PostgreSQL (${DB_HOST}:${DB_PORT})..."
  sleep 2
done

echo "✅ PostgreSQL disponible. Creando base si no existe..."

PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 <<'EOSQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak') THEN
    RAISE NOTICE 'Creando base de datos keycloak...';
    CREATE DATABASE keycloak OWNER postgres;
  ELSE
    RAISE NOTICE 'La base de datos keycloak ya existe.';
  END IF;
END
$$;
EOSQL

echo "✅ Base de datos Keycloak verificada."
