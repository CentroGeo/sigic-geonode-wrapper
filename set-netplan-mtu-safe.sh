#!/bin/bash
set -e

echo "🔍 Detectando interfaz principal..."

main_iface=$(ip route | awk '/default/ {print $5}' | head -n 1)

if [ -z "$main_iface" ]; then
    echo "❌ No se pudo detectar la interfaz con gateway por defecto."
    exit 1
fi

echo "✅ Interfaz principal detectada: $main_iface"

current_mtu=$(ip link show dev "$main_iface" | awk '/mtu/ {print $5}')
if [ "$current_mtu" -eq 1400 ]; then
    echo "✅ MTU ya está en 1400. No se requiere cambio."
else
    echo "⚙️ Estableciendo MTU a 1400..."
    sudo ip link set dev "$main_iface" mtu 1400
fi

# Buscar archivo YAML de Netplan
NETPLAN_FILE=$(find /etc/netplan -name '*.yaml' | head -n 1)

if [ -z "$NETPLAN_FILE" ]; then
    echo "❌ No se encontró archivo Netplan en /etc/netplan/"
    exit 1
fi

echo "📄 Archivo Netplan encontrado: $NETPLAN_FILE"

# Verificar si ya tiene mtu configurado
if grep -A 5 "$main_iface:" "$NETPLAN_FILE" | grep -q "mtu:"; then
    current_value=$(grep -A 5 "$main_iface:" "$NETPLAN_FILE" | grep "mtu:" | awk '{print $2}')
    if [ "$current_value" -eq 1400 ]; then
        echo "✅ Netplan ya tiene mtu: 1400 para $main_iface. No se modifica."
        exit 0
    else
        echo "✏️ Actualizando mtu de $current_value → 1400 en $NETPLAN_FILE"
        sudo cp "$NETPLAN_FILE" "$NETPLAN_FILE.bak.$(date +%Y%m%d%H%M%S)"
        sudo sed -i "/$main_iface:/,/^[^ ]/s/mtu: .*/mtu: 1400/" "$NETPLAN_FILE"
    fi
else
    echo "➕ Agregando mtu: 1400 a la interfaz $main_iface"
    sudo cp "$NETPLAN_FILE" "$NETPLAN_FILE.bak.$(date +%Y%m%d%H%M%S)"

    # Insertar línea mtu: 1400 debajo de la interfaz
    sudo awk -v iface="$main_iface" '
    $0 ~ iface":" {
        print; in_iface=1; next
    }
    in_iface && /^[ ]+[a-zA-Z0-9_]+:/ {
        print "      mtu: 1400"; in_iface=0
    }
    { print }
    ' "$NETPLAN_FILE" > /tmp/netplan_tmp.yaml

    sudo mv /tmp/netplan_tmp.yaml "$NETPLAN_FILE"
fi

echo "✅ Aplicando Netplan..."
sudo netplan apply
echo "🎉 Configuración persistente completada para $main_iface con mtu: 1400"
