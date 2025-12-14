#!/usr/bin/env bash
set -euo pipefail

REQ_FILE="requirements/bundle.txt"

echo "🔎 Validando versionado SIGIC…"

# 1. VERSION
if [[ ! -f VERSION ]]; then
  echo "❌ Falta archivo VERSION"
  exit 1
fi

WRAPPER_VERSION=$(cat VERSION)

if ! [[ "$WRAPPER_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "❌ VERSION inválida: $WRAPPER_VERSION"
  exit 1
fi

echo "✔ VERSION=$WRAPPER_VERSION"

# 2. GEONODE_VERSION
GEONODE_VERSION=$(grep -E '^# GEONODE_VERSION=' "$REQ_FILE" | sed 's/# GEONODE_VERSION=//')

if [[ -z "${GEONODE_VERSION:-}" ]]; then
  echo "❌ Falta # GEONODE_VERSION en $REQ_FILE"
  exit 1
fi

if ! [[ "$GEONODE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "❌ GEONODE_VERSION inválida: $GEONODE_VERSION"
  exit 1
fi

echo "✔ GEONODE_VERSION=$GEONODE_VERSION"

# 3. SIGIC_PATCH
SIGIC_PATCH=$(grep -E '^# SIGIC_PATCH=' "$REQ_FILE" | sed 's/# SIGIC_PATCH=//')

if [[ -z "${SIGIC_PATCH:-}" ]]; then
  echo "❌ Falta # SIGIC_PATCH en $REQ_FILE"
  exit 1
fi

if ! [[ "$SIGIC_PATCH" =~ ^[0-9]+$ ]]; then
  echo "❌ SIGIC_PATCH inválido: $SIGIC_PATCH"
  exit 1
fi

echo "✔ SIGIC_PATCH=$SIGIC_PATCH"

# 4. Tag canónico
if [[ "$SIGIC_PATCH" -eq 0 ]]; then
  TAG="${WRAPPER_VERSION}+gn${GEONODE_VERSION}"
else
  TAG="${WRAPPER_VERSION}+gn${GEONODE_VERSION}.sigic.${SIGIC_PATCH}"
fi

echo "🏷 Tag canónico: $TAG"
echo "✅ Validación OK"
