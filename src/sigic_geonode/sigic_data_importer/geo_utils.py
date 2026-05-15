# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Conversion de DataFrame tabular a GeoDataFrame y exportacion a GeoPackage.

Estrategias:
  - latlon: puntos desde columnas lat/lon del propio archivo.
  - inegi_*_key / *_name: join con capa MGN precargada en GeoNode.
"""

import logging
import os
import tempfile

import pandas as pd

from .models import IneiBaseLayer

logger = logging.getLogger(__name__)

def _df_from_latlon(df: pd.DataFrame, lat_field: str, lon_field: str):
    import geopandas as gpd
    from shapely.geometry import Point

    df = df.copy()
    df[lat_field] = pd.to_numeric(df[lat_field], errors="coerce")
    df[lon_field] = pd.to_numeric(df[lon_field], errors="coerce")
    df = df.dropna(subset=[lat_field, lon_field])
    geometry = [Point(lon, lat) for lon, lat in zip(df[lon_field], df[lat_field])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def _gdf_from_inegi_join(df: pd.DataFrame, join_field: str, layer_type: str, match_by: str):
    import geopandas as gpd
    from django.conf import settings
    from sqlalchemy import create_engine

    try:
        base = IneiBaseLayer.objects.get(layer_type=layer_type)
    except IneiBaseLayer.DoesNotExist:
        raise ValueError(
            f"No existe capa base INEGI tipo '{layer_type}'. "
            "Las capas INEGI no se cargaron correctamente al migrar la base de datos."
        )

    if not base.table_name:
        raise ValueError(
            f"La capa INEGI '{layer_type}' no tiene tabla asignada. "
            "Ejecuta: python manage.py migrate"
        )

    table_name = base.table_name
    ref_field = base.key_field if match_by == "key" else base.name_field

    geodata_url = getattr(settings, "GEODATABASE_URL", "")
    pg_url = geodata_url.replace("postgis://", "postgresql+psycopg2://", 1)
    engine = create_engine(pg_url)

    geo_df = gpd.read_postgis(
        f'SELECT "{ref_field}", geometry FROM "{table_name}"',
        engine,
        geom_col="geometry",
        crs="EPSG:4326",
    )

    df = df.copy()
    pad = 2 if layer_type == "estado" else 5
    if match_by == "name":
        df["_join_key"] = df[join_field].astype(str).str.strip().str.upper()
        geo_df["_join_key"] = geo_df[ref_field].astype(str).str.strip().str.upper()
    else:
        df["_join_key"] = df[join_field].astype(str).str.strip().str.zfill(pad)
        geo_df["_join_key"] = geo_df[ref_field].astype(str).str.strip().str.zfill(pad)

    merged = df.merge(geo_df[["_join_key", "geometry"]], on="_join_key", how="left")
    merged.drop(columns=["_join_key"], inplace=True)
    return gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")


def build_geodataframe(
    df: pd.DataFrame,
    geo_strategy: str,
    geo_field_lat: str = "",
    geo_field_lon: str = "",
    geo_field_join: str = "",
):
    if geo_strategy == "latlon":
        return _df_from_latlon(df, geo_field_lat, geo_field_lon)
    elif geo_strategy == "inegi_mun_key":
        return _gdf_from_inegi_join(df, geo_field_join, "municipio", "key")
    elif geo_strategy == "inegi_state_key":
        return _gdf_from_inegi_join(df, geo_field_join, "estado", "key")
    elif geo_strategy == "mun_name":
        return _gdf_from_inegi_join(df, geo_field_join, "municipio", "name")
    elif geo_strategy == "state_name":
        return _gdf_from_inegi_join(df, geo_field_join, "estado", "name")
    else:
        raise ValueError(f"Estrategia geografica desconocida: {geo_strategy}")


def export_to_geojson(gdf, layer_name: str) -> str:
    """Exporta GeoDataFrame a un GeoJSON temporal y retorna la ruta."""
    tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
    tmp.close()
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf.to_file(tmp.name, driver="GeoJSON")
    return tmp.name


def geo_preview(
    df: pd.DataFrame,
    geo_strategy: str,
    geo_field_lat: str = "",
    geo_field_lon: str = "",
    geo_field_join: str = "",
    max_features: int = 200,
) -> dict:
    """
    Genera un GeoJSON de preview (primeros N registros) para mostrar en el mapa.
    """
    try:
        sample = df.head(max_features)
        sample_size = len(sample)
        gdf = build_geodataframe(sample, geo_strategy, geo_field_lat, geo_field_lon, geo_field_join)
        gdf = gdf[gdf.geometry.notna()]
        matched = int(len(gdf))
        total = len(df)
        geojson = gdf[["geometry"]].to_json()
        return {
            "ok": True,
            "matched": matched,
            "sample_size": sample_size,
            "total": total,
            "geojson": geojson,
        }
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        return {"ok": False, "error": str(exc), "traceback": tb}
