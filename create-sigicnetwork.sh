#!/bin/bash
set -e

NETWORK_NAME="sigicnetwork"
TARGET_MTU=1360

echo "🔍 Verificando red Docker: $NETWORK_NAME..."

# Verificar si la red ya existe
if docker network inspect "$NETWORK_NAME" > /dev/null 2>&1; then
    echo "✅ Red $NETWORK_NAME existe. Verificando MTU..."

    current_mtu=$(docker network inspect "$NETWORK_NAME" -f '{{ index .Options "com.docker.network.driver.mtu" }}')

    if [ "$current_mtu" = "$TARGET_MTU" ]; then
        echo "🎯 Red $NETWORK_NAME ya tiene mtu: $TARGET_MTU. No se necesita cambio."
        exit 0
    else
        echo "⚠️ Red $NETWORK_NAME tiene mtu diferente ($current_mtu). Será recreada..."

        docker network rm "$NETWORK_NAME"
    fi
else
    echo "➕ Red $NETWORK_NAME no existe. Será creada..."
fi

# Crear la red con MTU correcto
docker network create \
  --driver bridge \
  --opt com.docker.network.driver.mtu="$TARGET_MTU" \
  "$NETWORK_NAME"

echo "✅ Red $NETWORK_NAME creada con mtu: $TARGET_MTU"
