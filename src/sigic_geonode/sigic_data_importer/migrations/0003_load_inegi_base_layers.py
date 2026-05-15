"""
Data migration: carga capas MGN INEGI (estados y municipios) directamente
en la base de datos geodata (PostGIS) y registra IneiBaseLayer.

Corre automaticamente con `manage.py migrate`. No requiere tokens ni comandos manuales.
Los archivos shp estan bundleados en sigic_data_importer/data/inegi/.
"""

import os
import tempfile
import zipfile

from django.db import migrations

# Configuracion de cada capa
LAYERS = [
    {
        "layer_type": "estado",
        "zip_name": "estados.zip",
        "shp_name": "dest22gw.shp",
        "table_name": "inegi_estados",
        "key_field": "CVEGEO",
        "name_field": "NOMGEO",
    },
    {
        "layer_type": "municipio",
        "zip_name": "municipios.zip",
        "shp_name": "mun22gw.shp",
        "table_name": "inegi_municipios",
        "key_field": "CVEGEO",
        "name_field": "NOMGEO",
    },
]


def _data_dir():
    return os.path.join(os.path.dirname(__file__), "..", "data", "inegi")


def _load_layer(layer_cfg, geodata_url):
    """Carga un shapefile INEGI a PostGIS y retorna True si tuvo exito."""
    try:
        import geopandas as gpd
        from sqlalchemy import create_engine, text

        zip_path = os.path.join(_data_dir(), layer_cfg["zip_name"])
        if not os.path.exists(zip_path):
            print(f"  [INEGI] Archivo no encontrado: {zip_path}")
            return False

        with zipfile.ZipFile(zip_path) as z:
            tmp = tempfile.mkdtemp()
            z.extractall(tmp)

        shp_path = os.path.join(tmp, layer_cfg["shp_name"])
        gdf = gpd.read_file(shp_path)

        # Reproyectar a WGS84 si es necesario
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        # Conservar solo columnas necesarias + geometry
        keep_cols = [layer_cfg["key_field"], layer_cfg["name_field"], "geometry"]
        extra = [c for c in ["CVE_ENT", "NOM_ENT"] if c in gdf.columns]
        gdf = gdf[keep_cols + extra].copy()

        # Convertir postgis:// a postgresql+psycopg2://
        pg_url = geodata_url.replace("postgis://", "postgresql+psycopg2://", 1)
        engine = create_engine(pg_url)

        table = layer_cfg["table_name"]
        gdf.to_postgis(table, engine, if_exists="replace", index=False)
        print(f"  [INEGI] Cargada '{layer_cfg['layer_type']}' → tabla '{table}' ({len(gdf)} filas)")
        return True

    except Exception as exc:
        print(f"  [INEGI] Error cargando '{layer_cfg['layer_type']}': {exc}")
        return False


def load_inegi_layers(apps, schema_editor):
    from django.conf import settings

    IneiBaseLayer = apps.get_model("sigic_data_importer", "IneiBaseLayer")

    geodata_url = getattr(settings, "GEODATABASE_URL", None)
    if not geodata_url:
        print("  [INEGI] GEODATABASE_URL no configurada, omitiendo carga automatica.")
        return

    for cfg in LAYERS:
        if IneiBaseLayer.objects.filter(layer_type=cfg["layer_type"]).exists():
            # Ya existe: actualizar solo table_name si falta
            obj = IneiBaseLayer.objects.get(layer_type=cfg["layer_type"])
            if not obj.table_name:
                obj.table_name = cfg["table_name"]
                obj.save(update_fields=["table_name"])
            print(f"  [INEGI] Capa '{cfg['layer_type']}' ya registrada, omitiendo.")
            continue

        ok = _load_layer(cfg, geodata_url)
        IneiBaseLayer.objects.create(
            layer_type=cfg["layer_type"],
            table_name=cfg["table_name"] if ok else "",
            key_field=cfg["key_field"],
            name_field=cfg["name_field"],
        )


def unload_inegi_layers(apps, schema_editor):
    """Reverse: elimina las tablas INEGI y los registros."""
    try:
        from django.conf import settings
        from sqlalchemy import create_engine, text

        geodata_url = getattr(settings, "GEODATABASE_URL", "")
        if geodata_url:
            pg_url = geodata_url.replace("postgis://", "postgresql+psycopg2://", 1)
            engine = create_engine(pg_url)
            with engine.connect() as conn:
                for cfg in LAYERS:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{cfg["table_name"]}"'))
                conn.commit()
    except Exception:
        pass

    IneiBaseLayer = apps.get_model("sigic_data_importer", "IneiBaseLayer")
    IneiBaseLayer.objects.filter(layer_type__in=[c["layer_type"] for c in LAYERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sigic_data_importer", "0002_ineibaselayer_table_name_alter_geonode_dataset_id"),
    ]

    operations = [
        migrations.RunPython(load_inegi_layers, reverse_code=unload_inegi_layers),
    ]
