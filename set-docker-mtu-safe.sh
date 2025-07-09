#!/bin/bash
set -e

DAEMON_JSON="/etc/docker/daemon.json"
MTU_VALUE=1360

echo "🔧 Configurando Docker para usar MTU $MTU_VALUE"

apt-get update && sudo apt-get install -y jq


# Crear archivo si no existe
if [ ! -f "$DAEMON_JSON" ]; then
    echo "📄 Archivo $DAEMON_JSON no existe. Creándolo..."
    echo "{ \"mtu\": $MTU_VALUE }" | sudo tee "$DAEMON_JSON" > /dev/null
else
    echo "📄 Archivo existente encontrado: $DAEMON_JSON"

    # Respaldar archivo existente
    sudo cp "$DAEMON_JSON" "$DAEMON_JSON.bak.$(date +%Y%m%d%H%M%S)"

    # Verificar si ya tiene mtu
    if grep -q '"mtu"' "$DAEMON_JSON"; then
        current=$(jq '.mtu' "$DAEMON_JSON")
        if [ "$current" -eq "$MTU_VALUE" ]; then
            echo "✅ Docker ya tiene mtu: $MTU_VALUE. No se modifica."
        else
            echo "✏️ Actualizando mtu de $current → $MTU_VALUE..."
            sudo jq ".mtu = $MTU_VALUE" "$DAEMON_JSON" | sudo tee "$DAEMON_JSON" > /dev/null
        fi
    else
        echo "➕ Agregando campo mtu: $MTU_VALUE..."
        sudo jq ". + {\"mtu\": $MTU_VALUE}" "$DAEMON_JSON" | sudo tee "$DAEMON_JSON" > /dev/null
    fi
fi

# Reiniciar Docker para aplicar
echo "🔄 Reiniciando Docker..."
sudo systemctl restart docker

echo "🎉 Docker configurado correctamente con MTU $MTU_VALUE"
