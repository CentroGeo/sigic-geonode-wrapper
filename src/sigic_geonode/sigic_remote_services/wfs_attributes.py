# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Sincronización de atributos WFS para capas remotas.

Para datasets con sourcetype=REMOTE cuyo attribute_set está vacío, obtiene el
esquema de columnas llamando a WFS DescribeFeatureType en el servidor remoto y
lo persiste en la tabla Attribute de GeoNode.
"""

import logging
from urllib.parse import urlparse, urlencode
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)

# Campos de geometría que se excluyen del attribute_set
_GEO_FIELDS = {"the_geom", "geometry", "geom", "wkb_geometry", "shape"}

# Fragmentos en el tipo XSD que indican geometría (para capas con tipos GML)
_GEO_TYPE_FRAGMENTS = (
    "geometryproperty",
    "pointproperty",
    "linestringproperty",
    "polygonproperty",
    "multipointproperty",
    "multilinestringproperty",
    "multipolygonproperty",
    "multigeometryproperty",
    "geometrycollectionproperty",
    "abstractgeometry",
)

# Tipos XSD → tipo GeoNode
_TYPE_MAP = {
    "xsd:string": "xsd:string",
    "xsd:int": "xsd:int",
    "xsd:integer": "xsd:int",
    "xsd:long": "xsd:long",
    "xsd:short": "xsd:short",
    "xsd:byte": "xsd:int",
    "xsd:float": "xsd:float",
    "xsd:double": "xsd:double",
    "xsd:decimal": "xsd:double",
    "xsd:boolean": "xsd:boolean",
    "xsd:date": "xsd:date",
    "xsd:dateTime": "xsd:dateTime",
    "xsd:time": "xsd:string",
    "xsd:anyURI": "xsd:string",
    "xsd:nonNegativeInteger": "xsd:int",
    "xsd:positiveInteger": "xsd:int",
}


def _base_url(url: str) -> str:
    """Strip query string and fragment, return scheme+host+path."""
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path}"


def _wfs_url(ows_url: str) -> str:
    """
    Derive the WFS endpoint from a WMS/OWS URL.

    Tries replacing common WMS paths with their WFS equivalents.
    Falls back to using the same base URL (GeoServer /ows accepts both).
    """
    base = _base_url(ows_url)
    lower = base.lower()
    if lower.endswith("/wms"):
        base = base[:-4] + "/wfs"
    # /ows already handles WFS requests — leave as-is
    return base


def _normalize_type(xsd_type: str) -> str:
    """Map an XSD type string to a GeoNode attribute_type value."""
    normalized = xsd_type if xsd_type.startswith("xsd:") else f"xsd:{xsd_type.split(':')[-1]}"
    return _TYPE_MAP.get(xsd_type, _TYPE_MAP.get(normalized, "xsd:string"))


def _is_geometry_field(name: str, xsd_type: str) -> bool:
    if name.lower() in _GEO_FIELDS:
        return True
    type_lower = xsd_type.lower()
    return any(frag in type_lower for frag in _GEO_TYPE_FRAGMENTS)


def _parse_describe_feature_type(xml_text: str) -> list:
    """
    Parse a WFS DescribeFeatureType XML response.

    Returns a list of dicts: [{"attribute": str, "attribute_type": str}, ...]
    Geometry fields are excluded.
    """
    root = ET.fromstring(xml_text)
    # xsd:element tags appear within xsd:sequence → iterate the whole tree
    xsd_ns = "http://www.w3.org/2001/XMLSchema"
    attrs = []
    for elem in root.iter(f"{{{xsd_ns}}}element"):
        name = elem.get("name")
        xsd_type = elem.get("type", "xsd:string")
        if not name:
            continue
        if _is_geometry_field(name, xsd_type):
            continue
        attrs.append({
            "attribute": name,
            "attribute_type": _normalize_type(xsd_type),
        })
    return attrs


def fetch_wfs_attributes(ows_url: str, typename: str, timeout: int = 20) -> list:
    """
    Call WFS DescribeFeatureType on the remote server for the given typename.

    Returns a list of attribute dicts, or [] on any error.
    """
    wfs_endpoint = _wfs_url(ows_url)
    qs = urlencode({
        "service": "WFS",
        "version": "2.0.0",
        "request": "DescribeFeatureType",
        "typeName": typename,
    })
    url = f"{wfs_endpoint}?{qs}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(
            "[SIGIC WFS] DescribeFeatureType falló para %s @ %s: %s",
            typename, wfs_endpoint, exc,
        )
        return []

    try:
        return _parse_describe_feature_type(resp.text)
    except Exception as exc:
        logger.warning(
            "[SIGIC WFS] No se pudo parsear DescribeFeatureType para %s: %s",
            typename, exc,
        )
        return []


def sync_attributes_from_wfs(dataset, force: bool = False) -> int:
    """
    Sync WFS attributes into GeoNode's Attribute table for a remote dataset.

    Skips datasets that already have attributes unless force=True.
    Returns the number of attributes upserted (0 if skipped or failed).
    """
    from geonode.layers.models import Attribute

    if dataset.sourcetype != "REMOTE":
        return 0

    if not force and dataset.attribute_set.exists():
        return 0

    # Prefer typename without harvester suffix (RemoteLayerTypename)
    typename = None
    try:
        from sigic_geonode.sigic_remote_services.models import RemoteLayerTypename
        rlt = RemoteLayerTypename.objects.filter(dataset=dataset).first()
        if rlt:
            typename = rlt.typename
    except Exception:
        pass

    if not typename:
        typename = getattr(dataset, "alternate", None)

    ows_url = getattr(dataset, "ows_url", None)

    if not ows_url or not typename:
        logger.debug(
            "[SIGIC WFS] Dataset %s: sin ows_url o typename, saltando sync",
            dataset.pk,
        )
        return 0

    attrs = fetch_wfs_attributes(ows_url, typename)
    if not attrs:
        return 0

    synced = 0
    for order, attr_data in enumerate(attrs, start=1):
        Attribute.objects.update_or_create(
            dataset=dataset,
            attribute=attr_data["attribute"],
            defaults={
                "attribute_type": attr_data["attribute_type"],
                "display_order": order,
                "visible": True,
            },
        )
        synced += 1

    logger.info(
        "[SIGIC WFS] Dataset %s (%s): %d atributos sincronizados",
        dataset.pk, typename, synced,
    )
    return synced
