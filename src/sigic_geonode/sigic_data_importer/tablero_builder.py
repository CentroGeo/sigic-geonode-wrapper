# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Creacion automatica de un tablero de datos a partir de un DataImportJob.

Crea: Site → SiteConfiguration → IndicatorGroups → Indicators (con datos
pre-calculados, infoboxes KPI, e indicadores categoricos si aplica).
"""

import logging
import re

from geonode.layers.models import Dataset

from sigic_geonode.sigic_dashboard.models import (
    IndicatorFieldBoxInfo,
    IndicatorGroup,
    Indicator,
    Site,
    SiteConfiguration,
)
from sigic_geonode.sigic_dashboard.utils.indicator_utils import (
    get_color_palette,
    process_data,
)

logger = logging.getLogger(__name__)

_NUMERIC_TYPES = {"entero", "decimal"}
_TEXT_TYPE = "texto"
_MAX_CATEGORICAL_UNIQUE = 12
_DEFAULT_PALETTES = ["azules_3", "cafes", "morados", "verdes_2", "naranjas", "rosas"]

# Campos técnicos que nunca deben convertirse en indicadores
_EXCLUDED_FIELD_NAMES = {"fid", "ogc_fid"}
# Roles geográficos que no son indicadores
_GEO_ROLES = {"lat", "lon", "state_key", "mun_key", "state_name", "mun_name"}


def _slugify(text: str, max_len: int = 200) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:max_len]


def _get_indicator_data(field_one, field_id, table_name, cast_numeric=False):
    """
    Obtiene datos crudos de la BD de geodatos usando la conexion de utils.geodata_conn.
    cast_numeric=True hace ::numeric sobre field_one para que process_data lo trate
    como numero (columnas varchar importadas desde CSV llegan como strings).
    Retorna lista de tuplas (field_one_val, field_id_val) o None si falla.
    """
    from sigic_geonode.utils.geodata_conn import connection
    try:
        connection.rollback()
    except Exception:
        pass
    try:
        with connection.cursor() as cur:
            # ::float8 retorna float nativo de Python (no Decimal) → pandas lo infiere como float64
            field_expr = f'"{field_one}"::float8' if cast_numeric else f'"{field_one}"'
            cur.execute(
                f'SELECT {field_expr}, "{field_id}" FROM "{table_name}"'
                f' WHERE "{field_one}" IS NOT NULL AND "{field_id}" IS NOT NULL'
            )
            return cur.fetchall()
    except Exception:
        logger.exception("_get_indicator_data failed for table=%s col=%s", table_name, field_one)
        try:
            connection.rollback()
        except Exception:
            pass
        return None


def _detect_nom_field(schema, geo_strategy):
    """
    Detecta el campo de nombre geografico desde el schema del job.
    Busca geo_role = 'state_name' o 'mun_name'.
    """
    if geo_strategy in ("latlon", "none"):
        return None
    for col in schema:
        if col.get("geo_role") in ("state_name", "mun_name"):
            return col["name"]
    return None


def _is_categorical(col):
    """
    Detecta si una columna de texto es categorica (pocos valores unicos en muestra).
    """
    tipo = col.get("editable_type") or col.get("detected_type")
    if tipo != _TEXT_TYPE:
        return False
    if col.get("geo_role"):
        return False
    unique = set(col.get("sample_values", []))
    return 1 < len(unique) <= _MAX_CATEGORICAL_UNIQUE


def _pre_compute_indicator(indicator, layer_name, palette_name, n_classes=5):
    """
    Calcula plot_values, map_values y plot_config para el indicador y los persiste.
    No-fatal: si falla, el indicador queda vacio (el usuario puede construirlo manualmente).
    """
    try:
        is_numeric = indicator.plot_type != "donut"
        data = _get_indicator_data(
            indicator.field_one, indicator.layer_id_field, layer_name, cast_numeric=is_numeric
        )
        if not data:
            return
        processed = process_data(
            data,
            indicator.field_one,
            indicator.layer_id_field,
            "quantil",
            n_classes,
            indicator,
            [],
        )
        if not processed or "error" in processed:
            logger.warning(
                "process_data error for indicator %s: %s",
                indicator.id,
                processed.get("error") if processed else "None",
            )
            return
        colors = get_color_palette(palette_name)
        raw_plot = processed.get("plot_data", [])
        raw_theming = processed.get("theming_data", {})

        # Asignar colores con cycling para evitar IndexError cuando hay más clases que colores
        color_by_label = {}
        plot_data = []
        for idx, row in enumerate(raw_plot):
            color = colors[idx % len(colors)]
            plot_data.append({**row, "color": color})
            color_by_label[row["label"]] = color

        theming_data = {
            geom_id: {**val, "color": color_by_label.get(val.get("value", ""), "#cccccc")}
            for geom_id, val in raw_theming.items()
        }

        indicator.plot_values = plot_data
        indicator.map_values = theming_data
        indicator.plot_config = {
            "chart_type": indicator.plot_type,
            "title": indicator.name,
            "ranges": [
                {
                    "alias": r["label"],
                    "count": r["value"],
                    "color": r.get("color", "#000000"),
                }
                for r in plot_data
            ],
        }
        indicator.colors = palette_name
        indicator.category_method = "quantil"
        indicator.field_category = n_classes
        indicator.save()
    except Exception:
        logger.exception("Pre-compute failed for indicator %s", indicator.id)


def _create_infobox(indicator, col_name, label, color="#691c32", order=1):
    """Crea un infobox KPI para el indicador. El valor se calcula en tiempo real (SUM)."""
    IndicatorFieldBoxInfo.objects.create(
        indicator=indicator,
        field=col_name,
        name=label,
        color=color,
        text_color="#ffffff",
        edge_style="8",
        size="1",
        stack_order=order,
    )


def build_tablero_from_job(job) -> int:
    """
    Crea un tablero automatico para el job indicado.

    Retorna el id del Site creado.
    """
    base_name = job.original_filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")

    site_name = base_name[:250]
    counter = 1
    while Site.objects.filter(name=site_name).exists():
        site_name = f"{base_name[:240]} ({counter})"
        counter += 1

    site = Site.objects.create(
        name=site_name,
        title=site_name,
        subtitle="Tablero generado automaticamente desde datos importados",
        url=_slugify(site_name),
        is_public=True,
    )

    SiteConfiguration.objects.create(
        site=site,
        show_header=True,
        show_footer=True,
        header_background_color="#691c32",
        header_text_color="#ffffff",
        header_font_size=28,
        site_font_style="Source Sans Pro",
        site_text_color="#333333",
        site_interface_text_color="#333333",
        site_background_color="#f5f5f5",
        site_interface_background_color="#ffffff",
        site_font_size=16,
        indicator_box_title="Indicador",
    )

    schema = job.column_schema or []

    # Campo ID geografico segun estrategia
    if job.geo_strategy in ("latlon", "none"):
        geo_id_field = "fid"
    else:
        geo_id_field = job.geo_field_join or "fid"

    geo_nom_field = _detect_nom_field(schema, job.geo_strategy)

    dataset = None
    layer_name = None
    if job.geonode_dataset_id:
        dataset = Dataset.objects.filter(id=job.geonode_dataset_id).first()
        if dataset:
            layer_name = dataset.name  # nombre de la tabla en geonode_data

    # Campos configurados como coordenadas o join geográfico (no deben ser indicadores)
    geo_configured = {
        f for f in [job.geo_field_lat, job.geo_field_lon, job.geo_field_join] if f
    }

    def _is_indicator_col(col):
        name = col.get("name", "")
        if name.lower() in _EXCLUDED_FIELD_NAMES:
            return False
        if name in geo_configured:
            return False
        if col.get("geo_role") in _GEO_ROLES:
            return False
        return True

    # Columnas para indicadores: preferir style_specs del usuario (paso 4)
    # Si no hay specs, caer en columnas numéricas del schema
    style_specs = [
        s for s in (job.style_specs or [])
        if s.get("col") and s.get("type") in ("graduated", "graduated_size", "categorical")
    ]

    categorical_cols = [c for c in schema if _is_categorical(c) and _is_indicator_col(c)]

    # --- Grupo principal: indicadores numéricos ---
    group = IndicatorGroup.objects.create(
        site=site,
        name="Indicadores",
        description="Indicadores generados automaticamente",
        stack_order=1,
    )

    if style_specs:
        # Usar las columnas configuradas por el usuario en el paso de estilos
        for idx, spec in enumerate(style_specs[:10], start=1):
            col_name = spec["col"]
            raw_label = spec.get("label") or col_name
            col_label = raw_label.replace("_", " ").title()
            palette = _DEFAULT_PALETTES[(idx - 1) % len(_DEFAULT_PALETTES)]

            indicator = Indicator.objects.create(
                site=site,
                group=group,
                name=col_label,
                plot_type="bar",
                layer=dataset,
                layer_id_field=geo_id_field,
                layer_nom_field=geo_nom_field,
                field_one=col_name,
                field_two="",
                use_single_field=True,
                show_general_values=True,
                stack_order=idx,
            )

            _create_infobox(indicator, col_name, f"Total: {col_label}")

            if layer_name:
                _pre_compute_indicator(indicator, layer_name, palette)
    else:
        # Fallback: columnas numéricas del schema excluyendo campos técnicos y geo
        numeric_cols = [
            c for c in schema
            if (c.get("editable_type") or c.get("detected_type")) in _NUMERIC_TYPES
            and _is_indicator_col(c)
        ]
        for idx, col in enumerate(numeric_cols[:10], start=1):
            col_name = col["name"]
            col_label = (col.get("label") or col_name).replace("_", " ").title()
            palette = _DEFAULT_PALETTES[(idx - 1) % len(_DEFAULT_PALETTES)]

            indicator = Indicator.objects.create(
                site=site,
                group=group,
                name=col_label,
                plot_type="bar",
                layer=dataset,
                layer_id_field=geo_id_field,
                layer_nom_field=geo_nom_field,
                field_one=col_name,
                field_two="",
                use_single_field=True,
                show_general_values=True,
                stack_order=idx,
            )

            _create_infobox(indicator, col_name, f"Total: {col_label}")

            if layer_name:
                _pre_compute_indicator(indicator, layer_name, palette)

    # --- Grupo categorico: distribucion de variables de texto ---
    if categorical_cols and dataset and layer_name:
        cat_group = IndicatorGroup.objects.create(
            site=site,
            name="Distribución categórica",
            description="Distribución de variables categóricas",
            stack_order=2,
        )
        for idx, col in enumerate(categorical_cols[:5], start=1):
            col_name = col["name"]
            col_label = (col.get("label") or col_name).replace("_", " ").title()

            indicator = Indicator.objects.create(
                site=site,
                group=cat_group,
                name=f"Distribución: {col_label}",
                plot_type="donut",
                layer=dataset,
                layer_id_field=geo_id_field,
                layer_nom_field=geo_nom_field,
                field_one=col_name,
                field_two="",
                use_single_field=True,
                show_general_values=True,
                stack_order=idx,
            )

            _create_infobox(indicator, "__count__", "Total registros", order=1)
            _pre_compute_indicator(indicator, layer_name, "varios", n_classes=5)

    return site.id
