# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Deteccion automatica de tipos de columnas usando pandas.

Prioridad: heuristicas deterministicas primero; IA (Ollama) solo
si el usuario activa explicitamente el analisis asistido.
"""

import re

import pandas as pd

# Nombres canonicos de campos geograficos
_LAT_NAMES = {"lat", "latitude", "latitud", "y", "lat_dd", "latgd"}
_LON_NAMES = {"lon", "lng", "longitude", "longitud", "x", "lon_dd", "longd", "lngd"}
_STATE_KEY_NAMES = {"cve_ent", "cvgeo_ent", "estado_id", "clave_estado", "ent", "entidad_cve"}
_MUN_KEY_NAMES = {"cve_mun", "cvegeo", "cve_geo", "cvegeomun", "municipio_id", "clave_municipio", "mun_id"}
_STATE_NAME_NAMES = {"nombre_estado", "nom_ent", "entidad", "estado", "state_name", "state"}
_MUN_NAME_NAMES = {"nombre_municipio", "nom_mun", "municipio", "municipality"}

_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d",
    "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y",
]


def _has_leading_zeros(series: pd.Series) -> bool:
    """True si alguna muestra no nula tiene cero al inicio."""
    sample = series.dropna().astype(str).head(50)
    return any(v.startswith("0") and len(v) > 1 for v in sample)


def _try_parse_dates(series: pd.Series) -> bool:
    """True si >80% de los valores no nulos parsean como fecha."""
    sample = series.dropna().head(100)
    if len(sample) == 0:
        return False
    hits = 0
    for fmt in _DATE_FORMATS:
        try:
            parsed = pd.to_datetime(sample, format=fmt, errors="coerce")
            ratio = parsed.notna().sum() / len(sample)
            if ratio > 0.8:
                return True
        except Exception:
            continue
    # Generic parse as last resort
    try:
        parsed = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
        hits = parsed.notna().sum()
    except Exception:
        pass
    return hits / len(sample) > 0.8


def _infer_column(col_name: str, series: pd.Series) -> dict:
    """Devuelve dict con detected_type, confidence y suggested_geo_role."""
    name_lower = col_name.strip().lower()
    dtype = series.dtype
    non_null = series.dropna()
    sample = non_null.head(5).tolist()
    confidence = "high"
    geo_role = None

    # --- Geografico: lat ---
    if name_lower in _LAT_NAMES:
        try:
            vals = pd.to_numeric(non_null, errors="coerce").dropna()
            if vals.between(-90, 90).mean() > 0.9:
                return {"detected_type": "latitud", "confidence": "high", "geo_role": "lat", "sample_values": sample}
        except Exception:
            pass

    # --- Geografico: lon ---
    if name_lower in _LON_NAMES:
        try:
            vals = pd.to_numeric(non_null, errors="coerce").dropna()
            if vals.between(-180, 180).mean() > 0.9:
                return {"detected_type": "longitud", "confidence": "high", "geo_role": "lon", "sample_values": sample}
        except Exception:
            pass

    # --- Clave estado INEGI (2 digitos) ---
    if name_lower in _STATE_KEY_NAMES:
        return {"detected_type": "texto", "confidence": "high", "geo_role": "state_key", "sample_values": sample}

    # --- Clave municipio INEGI (5 digitos) ---
    if name_lower in _MUN_KEY_NAMES:
        return {"detected_type": "texto", "confidence": "high", "geo_role": "mun_key", "sample_values": sample}

    # --- Nombre estado ---
    if name_lower in _STATE_NAME_NAMES:
        return {"detected_type": "texto", "confidence": "high", "geo_role": "state_name", "sample_values": sample}

    # --- Nombre municipio ---
    if name_lower in _MUN_NAME_NAMES:
        return {"detected_type": "texto", "confidence": "high", "geo_role": "mun_name", "sample_values": sample}

    # --- Numerico con leading zeros → texto (ej. CP, claves) ---
    if pd.api.types.is_integer_dtype(dtype) or pd.api.types.is_float_dtype(dtype):
        if _has_leading_zeros(series):
            return {"detected_type": "texto", "confidence": "medium",
                    "geo_role": None, "sample_values": sample,
                    "warning": "Numerico con ceros iniciales detectado como texto (ej. codigo postal)"}

    # --- Numerico puro ---
    if pd.api.types.is_integer_dtype(dtype):
        return {"detected_type": "entero", "confidence": "high", "geo_role": None, "sample_values": sample}
    if pd.api.types.is_float_dtype(dtype):
        return {"detected_type": "decimal", "confidence": "high", "geo_role": None, "sample_values": sample}

    # --- Objeto: intentar parsear como numero ---
    if pd.api.types.is_object_dtype(dtype):
        num_parsed = pd.to_numeric(non_null, errors="coerce")
        num_ratio = num_parsed.notna().sum() / max(len(non_null), 1)

        if num_ratio > 0.95:
            if _has_leading_zeros(series):
                return {"detected_type": "texto", "confidence": "medium",
                        "geo_role": None, "sample_values": sample,
                        "warning": "Ceros iniciales detectados; tratado como texto"}
            # Distinguir entero vs decimal
            if (num_parsed.dropna() % 1 == 0).all():
                return {"detected_type": "entero", "confidence": "high", "geo_role": None, "sample_values": sample}
            return {"detected_type": "decimal", "confidence": "high", "geo_role": None, "sample_values": sample}

        # Mixto (parte numerica, parte texto)
        if 0.1 < num_ratio < 0.95:
            return {"detected_type": "texto", "confidence": "low",
                    "geo_role": None, "sample_values": sample,
                    "warning": "Columna mixta (numeros y texto); requiere revision manual"}

        # Intentar fecha
        if _try_parse_dates(non_null):
            return {"detected_type": "fecha", "confidence": "medium", "geo_role": None, "sample_values": sample}

        return {"detected_type": "texto", "confidence": "high", "geo_role": None, "sample_values": sample}

    if pd.api.types.is_bool_dtype(dtype):
        return {"detected_type": "booleano", "confidence": "high", "geo_role": None, "sample_values": sample}

    if pd.api.types.is_datetime64_any_dtype(dtype):
        return {"detected_type": "fecha", "confidence": "high", "geo_role": None, "sample_values": sample}

    return {"detected_type": "texto", "confidence": "low", "geo_role": None, "sample_values": sample}


def detect_schema(df: pd.DataFrame) -> list:
    """
    Analiza un DataFrame y devuelve el esquema de columnas detectado.

    Retorna lista de dicts con:
      name, detected_type, editable_type, confidence, geo_role,
      sample_values, warning (opcional)
    """
    schema = []
    for col in df.columns:
        info = _infer_column(col, df[col])
        entry = {
            "name": col,
            "detected_type": info["detected_type"],
            "editable_type": "decimal" if info["detected_type"] in ("latitud", "longitud") else info["detected_type"],
            "confidence": info.get("confidence", "high"),
            "geo_role": info.get("geo_role"),
            "sample_values": [str(v) for v in info.get("sample_values", [])],
        }
        if "warning" in info:
            entry["warning"] = info["warning"]
        schema.append(entry)
    return schema


def suggest_geo_strategy(schema: list) -> dict:
    """
    A partir del schema detectado, sugiere la mejor estrategia geografica.

    Retorna dict con: strategy, lat_field, lon_field, join_field
    """
    lat_col = next((c["name"] for c in schema if c.get("geo_role") == "lat"), None)
    lon_col = next((c["name"] for c in schema if c.get("geo_role") == "lon"), None)
    # Prefer the 5-digit composite key (state+municipality) over the 3-digit municipal-only code
    mun_key_cols = [c for c in schema if c.get("geo_role") == "mun_key"]
    mun_key = next(
        (c["name"] for c in mun_key_cols if any(len(str(v).strip()) == 5 for v in (c.get("sample_values") or []))),
        next((c["name"] for c in mun_key_cols), None),
    )
    state_key = next((c["name"] for c in schema if c.get("geo_role") == "state_key"), None)
    mun_name = next((c["name"] for c in schema if c.get("geo_role") == "mun_name"), None)
    state_name = next((c["name"] for c in schema if c.get("geo_role") == "state_name"), None)

    if lat_col and lon_col:
        return {"strategy": "latlon", "lat_field": lat_col, "lon_field": lon_col, "join_field": ""}
    if mun_key:
        return {"strategy": "inegi_mun_key", "lat_field": "", "lon_field": "", "join_field": mun_key}
    if state_key:
        return {"strategy": "inegi_state_key", "lat_field": "", "lon_field": "", "join_field": state_key}
    if mun_name:
        return {"strategy": "mun_name", "lat_field": "", "lon_field": "", "join_field": mun_name}
    if state_name:
        return {"strategy": "state_name", "lat_field": "", "lon_field": "", "join_field": state_name}
    return {"strategy": "none", "lat_field": "", "lon_field": "", "join_field": ""}
