import logging
import re

import requests
from psycopg2.sql import SQL, Identifier

from .utils import get_name_from_ds

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color palettes (ColorBrewer)
# ---------------------------------------------------------------------------

QUALITATIVE_PALETTE = [
    "#8DD3C7",
    "#FFFFB3",
    "#BEBADA",
    "#FB8072",
    "#80B1D3",
    "#FDB462",
    "#B3DE69",
    "#FCCDE5",
    "#D9D9D9",
    "#BC80BD",
    "#CCEBC5",
    "#FFED6F",
    "#A6CEE3",
    "#1F78B4",
    "#B2DF8A",
]

SEQUENTIAL_PALETTE_5 = [
    "#FFFFB2",  # class 1 — lowest
    "#FECC5C",  # class 2
    "#FD8D3C",  # class 3
    "#F03B20",  # class 4
    "#BD0026",  # class 5 — highest
]

# ---------------------------------------------------------------------------
# Column classification constants
# ---------------------------------------------------------------------------

ID_LIKE_PATTERNS = re.compile(
    r"(^id$|_id$|^id_|^ogc_fid$|^fid$|^pk$|^codigo$|^clave$|^cve|^cvegeo$|^key$)",
    re.IGNORECASE,
)

STRING_TYPES = {"character varying", "varchar", "text", "character", "char", "bpchar"}

NUMERIC_TYPES = {
    "integer",
    "bigint",
    "smallint",
    "numeric",
    "decimal",
    "real",
    "double precision",
    "float4",
    "float8",
    "int4",
    "int8",
}

CATEGORICAL_MAX_STRING = 15
CATEGORICAL_MAX_NUMERIC = 10

# ---------------------------------------------------------------------------
# Symbolizer templates per geometry type
# ---------------------------------------------------------------------------

_SYMBOLIZER = {
    "Polygon": (
        "<PolygonSymbolizer>\n"
        "          <Fill>"
        '<CssParameter name="fill">{color}</CssParameter>'
        "</Fill>\n"
        "          <Stroke>\n"
        '            <CssParameter name="stroke">#666666</CssParameter>\n'
        '            <CssParameter name="stroke-width">0.5</CssParameter>\n'
        "          </Stroke>\n"
        "        </PolygonSymbolizer>"
    ),
    "Line": (
        "<LineSymbolizer>\n"
        "          <Stroke>\n"
        '            <CssParameter name="stroke">{color}</CssParameter>\n'
        '            <CssParameter name="stroke-width">2</CssParameter>\n'
        "          </Stroke>\n"
        "        </LineSymbolizer>"
    ),
    "Point": (
        "<PointSymbolizer>\n"
        "          <Graphic>\n"
        "            <Mark>\n"
        "              <WellKnownName>circle</WellKnownName>\n"
        "              <Fill>"
        '<CssParameter name="fill">{color}</CssParameter>'
        "</Fill>\n"
        "            </Mark>\n"
        "            <Size>8</Size>\n"
        "          </Graphic>\n"
        "        </PointSymbolizer>"
    ),
}

_SLD_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<StyledLayerDescriptor version="1.0.0"\n'
    '  xmlns="http://www.opengis.net/sld"\n'
    '  xmlns:ogc="http://www.opengis.net/ogc"\n'
    '  xmlns:xlink="http://www.w3.org/1999/xlink"\n'
    '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
    '  xsi:schemaLocation="http://www.opengis.net/sld '
    'http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">'
)


# ---------------------------------------------------------------------------
# Geometry type detection
# ---------------------------------------------------------------------------


def get_geometry_type(layer_name: str, cur) -> str:
    """Return 'Polygon', 'Line', or 'Point' from the geometry_columns view."""
    cur.execute(
        "SELECT type FROM geometry_columns WHERE f_table_name = %s LIMIT 1",
        [layer_name],
    )
    row = cur.fetchone()
    if row is None:
        return "Polygon"
    geom_type = row[0].upper()
    if "POLYGON" in geom_type or "SURFACE" in geom_type:
        return "Polygon"
    if "LINE" in geom_type or "CURVE" in geom_type:
        return "Line"
    return "Point"


# ---------------------------------------------------------------------------
# Column classification
# ---------------------------------------------------------------------------


def classify_column(layer_name: str, col_name: str, cur) -> dict:
    """
    Return {"kind": "categorical"|"numeric"|"skip", "pg_type": str|None}.

    Rules:
    - ID-like name → skip
    - string type, ≤15 distinct → categorical
    - string type, >15 distinct → skip
    - numeric type, ≤10 distinct → categorical
    - numeric type, >10 distinct → numeric
    - anything else → skip
    """
    if ID_LIKE_PATTERNS.search(col_name):
        return {"kind": "skip", "pg_type": None}

    cur.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s AND table_schema = 'public'
        LIMIT 1
        """,
        [layer_name, col_name],
    )
    row = cur.fetchone()
    if row is None:
        return {"kind": "skip", "pg_type": None}

    pg_type = row[0].lower()

    if pg_type in STRING_TYPES:
        cur.execute(
            SQL("SELECT COUNT(DISTINCT {col}) FROM {table}").format(
                col=Identifier(col_name),
                table=Identifier(layer_name),
            )
        )
        distinct = cur.fetchone()[0]
        if distinct <= CATEGORICAL_MAX_STRING:
            return {"kind": "categorical", "pg_type": pg_type}
        return {"kind": "skip", "pg_type": pg_type}

    if pg_type in NUMERIC_TYPES:
        cur.execute(
            SQL("SELECT COUNT(DISTINCT {col}) FROM {table}").format(
                col=Identifier(col_name),
                table=Identifier(layer_name),
            )
        )
        distinct = cur.fetchone()[0]
        if distinct <= CATEGORICAL_MAX_NUMERIC:
            return {"kind": "categorical", "pg_type": pg_type}
        return {"kind": "numeric", "pg_type": pg_type}

    return {"kind": "skip", "pg_type": pg_type}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def get_categorical_values(layer_name: str, col_name: str, cur) -> list:
    """Return sorted distinct non-null string values for a categorical column."""
    cur.execute(
        SQL(
            "SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL ORDER BY {col}"
        ).format(
            col=Identifier(col_name),
            table=Identifier(layer_name),
        )
    )
    return [str(row[0]) for row in cur.fetchall()]


def get_quantile_breaks(layer_name: str, col_name: str, cur, n: int = 5) -> list:
    """
    Return n+1 boundary values for n quantile classes using percentile_cont.
    Example for n=5: [min, p20, p40, p60, p80, max].

    col_name must match ^[A-Za-z0-9_]+$ (validated in generate_and_register_styles).
    """
    fractions = [i / n for i in range(1, n)]
    percentile_parts = ", ".join(
        f"percentile_cont({f}) WITHIN GROUP (ORDER BY {col_name})" for f in fractions
    )
    query = (
        f"SELECT MIN({col_name}), {percentile_parts}, MAX({col_name}) "
        f"FROM {layer_name} WHERE {col_name} IS NOT NULL"
    )
    cur.execute(query)
    row = cur.fetchone()
    if row is None or row[0] is None:
        return []
    return [float(v) for v in row]


# ---------------------------------------------------------------------------
# SLD XML builders
# ---------------------------------------------------------------------------


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_categorical_sld(
    layer_name: str,
    col_name: str,
    values: list,
    geom_type: str,
    style_name: str,
) -> str:
    """Build a complete SLD 1.0.0 for categorical classification."""
    rules = []
    for i, val in enumerate(values):
        color = QUALITATIVE_PALETTE[i % len(QUALITATIVE_PALETTE)]
        symbolizer = _SYMBOLIZER[geom_type].format(color=color)
        escaped = _xml_escape(val)
        rules.append(
            f"    <Rule>\n"
            f"      <Name>{escaped}</Name>\n"
            f"      <Title>{escaped}</Title>\n"
            f"      <ogc:Filter>\n"
            f"        <ogc:PropertyIsEqualTo>\n"
            f"          <ogc:PropertyName>{col_name}</ogc:PropertyName>\n"
            f"          <ogc:Literal>{escaped}</ogc:Literal>\n"
            f"        </ogc:PropertyIsEqualTo>\n"
            f"      </ogc:Filter>\n"
            f"      {symbolizer}\n"
            f"    </Rule>"
        )
    null_sym = _SYMBOLIZER[geom_type].format(color="#CCCCCC")
    rules.append(
        f"    <Rule>\n"
        f"      <Name>Sin datos</Name>\n"
        f"      <Title>Sin datos</Title>\n"
        f"      <ElseFilter/>\n"
        f"      {null_sym}\n"
        f"    </Rule>"
    )
    rules_str = "\n".join(rules)
    return (
        f"{_SLD_HEADER}\n"
        f"  <NamedLayer>\n"
        f"    <Name>{layer_name}</Name>\n"
        f"    <UserStyle>\n"
        f"      <Title>{col_name} - Categórico</Title>\n"
        f"      <FeatureTypeStyle>\n"
        f"{rules_str}\n"
        f"      </FeatureTypeStyle>\n"
        f"    </UserStyle>\n"
        f"  </NamedLayer>\n"
        f"</StyledLayerDescriptor>"
    )


def build_numeric_sld(
    layer_name: str,
    col_name: str,
    breaks: list,
    geom_type: str,
    style_name: str,
) -> str:
    """Build a complete SLD 1.0.0 for numeric quantile classification (5 classes)."""
    n = len(breaks) - 1
    palette = SEQUENTIAL_PALETTE_5[:n]
    rules = []
    for i in range(n):
        color = palette[i]
        low = breaks[i]
        high = breaks[i + 1]
        symbolizer = _SYMBOLIZER[geom_type].format(color=color)
        label = f"{low:.4g} – {high:.4g}"
        rules.append(
            f"    <Rule>\n"
            f"      <Name>{label}</Name>\n"
            f"      <Title>{label}</Title>\n"
            f"      <ogc:Filter>\n"
            f"        <ogc:And>\n"
            f"          <ogc:PropertyIsGreaterThanOrEqualTo>\n"
            f"            <ogc:PropertyName>{col_name}</ogc:PropertyName>\n"
            f"            <ogc:Literal>{low}</ogc:Literal>\n"
            f"          </ogc:PropertyIsGreaterThanOrEqualTo>\n"
            f"          <ogc:PropertyIsLessThanOrEqualTo>\n"
            f"            <ogc:PropertyName>{col_name}</ogc:PropertyName>\n"
            f"            <ogc:Literal>{high}</ogc:Literal>\n"
            f"          </ogc:PropertyIsLessThanOrEqualTo>\n"
            f"        </ogc:And>\n"
            f"      </ogc:Filter>\n"
            f"      {symbolizer}\n"
            f"    </Rule>"
        )
    null_sym = _SYMBOLIZER[geom_type].format(color="#CCCCCC")
    rules.append(
        f"    <Rule>\n"
        f"      <Name>Sin datos</Name>\n"
        f"      <Title>Sin datos</Title>\n"
        f"      <ElseFilter/>\n"
        f"      {null_sym}\n"
        f"    </Rule>"
    )
    rules_str = "\n".join(rules)
    return (
        f"{_SLD_HEADER}\n"
        f"  <NamedLayer>\n"
        f"    <Name>{layer_name}</Name>\n"
        f"    <UserStyle>\n"
        f"      <Title>{col_name} - Numérico (cuantiles)</Title>\n"
        f"      <FeatureTypeStyle>\n"
        f"{rules_str}\n"
        f"      </FeatureTypeStyle>\n"
        f"    </UserStyle>\n"
        f"  </NamedLayer>\n"
        f"</StyledLayerDescriptor>"
    )


# ---------------------------------------------------------------------------
# GeoServer + GeoNode registration
# ---------------------------------------------------------------------------


def push_style_to_geoserver(style_name: str, sld_body: str, layer_alternate: str) -> None:
    """
    Create/update a style in GeoServer and associate it with the layer.

    Steps (same pattern as sigic_styles/views.py):
    1. POST /rest/workspaces/{ws}/styles  — create style entry
    2. PUT  /rest/workspaces/{ws}/styles/{name}  — upload SLD
    3. POST /rest/layers/{alternate}/styles  — associate with layer
    """
    from django.conf import settings

    gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
    auth = (
        settings.OGC_SERVER["default"]["USER"],
        settings.OGC_SERVER["default"]["PASSWORD"],
    )
    workspace = layer_alternate.split(":")[0]  # "geonode"

    # 1. Create style entry
    wrapper = (
        f"<style>"
        f"<name>{style_name}</name>"
        f"<filename>{style_name}.sld</filename>"
        f"</style>"
    )
    r = requests.post(
        f"{gs_url}/rest/workspaces/{workspace}/styles",
        data=wrapper,
        auth=auth,
        headers={"Content-Type": "text/xml"},
        timeout=15,
    )
    if r.status_code not in (200, 201, 409):
        raise Exception(
            f"GeoServer rejected style creation for {style_name}: "
            f"{r.status_code} {r.text}"
        )

    # 2. Upload SLD content (apply fix for QGIS/SLD 1.1.0 compatibility)
    from sigic_geonode.utils.sld_utils import fix_sld, needs_fix

    if needs_fix(sld_body):
        sld_body = fix_sld(sld_body)

    r = requests.put(
        f"{gs_url}/rest/workspaces/{workspace}/styles/{style_name}",
        data=sld_body.encode("utf-8"),
        auth=auth,
        headers={"Content-Type": "application/vnd.ogc.sld+xml"},
        timeout=15,
    )
    if r.status_code not in (200, 201):
        raise Exception(
            f"GeoServer rejected SLD upload for {style_name}: "
            f"{r.status_code} {r.text}"
        )

    # 3. Associate with layer
    r = requests.post(
        f"{gs_url}/rest/layers/{layer_alternate}/styles",
        data=f"<style><name>{style_name}</name></style>",
        auth=auth,
        headers={"Content-Type": "application/xml"},
        timeout=15,
    )
    if r.status_code not in (200, 201):
        raise Exception(
            f"GeoServer rejected style association {style_name} → {layer_alternate}: "
            f"{r.status_code} {r.text}"
        )


def register_style_in_geonode(ds, style_name: str, sld_body: str):
    """
    Create (or update) a GeoNode Style record and associate it with the dataset.
    The generated style is NOT set as the dataset's default_style.
    """
    from django.conf import settings

    from geonode.layers.models import Style

    gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
    sld_url = f"{gs_url}/rest/workspaces/geonode/styles/{style_name}.sld"

    sty, _ = Style.objects.get_or_create(
        name=style_name,
        defaults={
            "sld_title": style_name,
            "workspace": "geonode",
            "sld_body": sld_body,
            "sld_version": "1.0.0",
            "sld_url": sld_url,
        },
    )
    if sty.sld_body != sld_body:
        sty.sld_body = sld_body
        sty.sld_url = sld_url
        sty.save()

    sty.dataset_styles.add(ds)
    return sty


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

_SAFE_COL = re.compile(r"^[A-Za-z0-9_]+$")


def generate_and_register_styles(ds, data_columns: list) -> None:
    """
    Entry point called from the Celery task generate_column_styles.

    For each column in data_columns:
    1. Validate name safety
    2. Classify (categorical / numeric / skip)
    3. Generate SLD
    4. Push to GeoServer
    5. Register in GeoNode

    Failures per column are logged but do not abort the loop.
    """
    from sigic_geonode.utils.geodata_conn import connection

    layer_name = get_name_from_ds(ds)

    with connection.cursor() as cur:
        geom_type = get_geometry_type(layer_name, cur)

        for col_name in data_columns:
            if not _SAFE_COL.match(col_name):
                logger.warning(f"Skipping unsafe column name: {col_name!r}")
                continue

            classification = classify_column(layer_name, col_name, cur)
            kind = classification["kind"]

            if kind == "skip":
                logger.info(f"Column {col_name} classified as skip, skipping style")
                continue

            style_name = f"{layer_name}__{col_name}"
            sld_body = None

            try:
                if kind == "categorical":
                    values = get_categorical_values(layer_name, col_name, cur)
                    if not values:
                        logger.info(f"No values for categorical column {col_name}, skipping")
                        continue
                    sld_body = build_categorical_sld(
                        layer_name, col_name, values, geom_type, style_name
                    )
                elif kind == "numeric":
                    breaks = get_quantile_breaks(layer_name, col_name, cur, n=5)
                    if not breaks or len(breaks) < 2:
                        logger.info(f"No valid breaks for numeric column {col_name}, skipping")
                        continue
                    sld_body = build_numeric_sld(
                        layer_name, col_name, breaks, geom_type, style_name
                    )
            except Exception as e:
                logger.error(f"SLD generation failed for column {col_name}: {e}")
                continue

            try:
                push_style_to_geoserver(style_name, sld_body, ds.alternate)
                register_style_in_geonode(ds, style_name, sld_body)
                logger.info(f"Style {style_name} created for dataset {ds.id}")
            except Exception as e:
                logger.error(f"Style registration failed for {style_name}: {e}")
                continue
