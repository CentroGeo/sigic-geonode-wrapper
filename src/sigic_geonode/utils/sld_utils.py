import re


OGC_NS = 'xmlns:ogc="http://www.opengis.net/ogc"'
SLD_NS = 'xmlns:sld="http://www.opengis.net/sld"'


def _get_root_tag(xml: str) -> str:
    m = re.search(r"<(?:sld:)?StyledLayerDescriptor\b[^>]*>", xml)
    return m.group(0) if m else ""


def needs_fix(xml: str) -> bool:
    """Detecta si un SLD requiere corrección (QGIS, SLD 1.1.0, etc.)."""
    if isinstance(xml, bytes):
        xml = xml.decode("utf-8")
    root = _get_root_tag(xml)
    return (
        'version="1.1.0"' in xml
        or 'xmlns:se="http://www.opengis.net/se"' in xml
        or re.search(r"\bse:", xml) is not None
        or re.search(r"<(/?)(?:se:|sld:)?SvgParameter\b", xml) is not None
        or (re.search(r"\bogc:", xml) is not None and OGC_NS not in root)
        or (re.search(r"\bsld:", xml) is not None and SLD_NS not in root)
        or re.search(r"<ogc:PropertyName>\s*[A-Z0-9_]+\s*</ogc:PropertyName>", xml) is not None
    )


def _ensure_root_prefix(xml: str) -> str:
    xml = re.sub(r"<StyledLayerDescriptor\b", "<sld:StyledLayerDescriptor", xml)
    xml = re.sub(r"</StyledLayerDescriptor>", "</sld:StyledLayerDescriptor>", xml)
    return xml


def _ensure_namespace_in_root(xml: str, namespace_decl: str) -> str:
    root = _get_root_tag(xml)
    if not root or namespace_decl in root:
        return xml
    new_root = root[:-1] + f" {namespace_decl}>"
    return xml.replace(root, new_root, 1)


def _normalize_schema_location(xml: str) -> str:
    replacement = (
        'xsi:schemaLocation="http://www.opengis.net/sld '
        'http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd"'
    )
    if "xsi:schemaLocation=" in xml:
        xml = re.sub(r'xsi:schemaLocation="[^"]+"', replacement, xml, count=1)
    else:
        root = _get_root_tag(xml)
        if root:
            new_root = root[:-1] + f" {replacement}>"
            xml = xml.replace(root, new_root, 1)
    return xml


def _convert_svg_to_css_parameter(xml: str) -> str:
    xml = re.sub(r"<(/?)se:SvgParameter\b", r"<\1sld:CssParameter", xml)
    xml = re.sub(r"<(/?)sld:SvgParameter\b", r"<\1sld:CssParameter", xml)
    xml = re.sub(r"<(/?)SvgParameter\b", r"<\1CssParameter", xml)
    return xml


def _lowercase_property_names(xml: str) -> str:
    """Convierte valores de ogc:PropertyName a minúsculas (QGIS exporta nombres en MAYÚSCULAS)."""
    def repl(match: re.Match) -> str:
        value = match.group(1).strip()
        return f"<ogc:PropertyName>{value.lower()}</ogc:PropertyName>"

    return re.sub(
        r"<ogc:PropertyName>\s*([^<]+?)\s*</ogc:PropertyName>",
        repl,
        xml,
    )


def fix_sld(xml) -> str:
    """
    Normalización completa de SLD para compatibilidad con GeoServer.
    Acepta str o bytes. Retorna str.

    Transformaciones (en orden):
    1. version="1.1.0" → "1.0.0"
    2. xmlns:se → xmlns:sld
    3. se: → sld: (prefijos de elementos y atributos)
    4. Raíz: <StyledLayerDescriptor → <sld:StyledLayerDescriptor
    5. Asegura xmlns:sld en la raíz
    6. Asegura xmlns:ogc en la raíz si hay referencias ogc:
    7. Corrige/agrega xsi:schemaLocation a SLD 1.0.0
    8. SvgParameter → CssParameter (maneja prefijos se:, sld: y sin prefijo)
    9. Convierte ogc:PropertyName a minúsculas
    10. Normaliza <sld:ElseFilter/> vacío
    11. Elimina <sld:Name></sld:Name> vacíos
    """
    if isinstance(xml, bytes):
        xml = xml.decode("utf-8")

    xml = re.sub(r'version="1\.1\.0"', 'version="1.0.0"', xml)
    xml = xml.replace(
        'xmlns:se="http://www.opengis.net/se"',
        'xmlns:sld="http://www.opengis.net/sld"',
    )
    xml = re.sub(r"\bse:", "sld:", xml)
    xml = _ensure_root_prefix(xml)
    xml = _ensure_namespace_in_root(xml, SLD_NS)
    if re.search(r"\bogc:", xml):
        xml = _ensure_namespace_in_root(xml, OGC_NS)
    xml = _normalize_schema_location(xml)
    xml = _convert_svg_to_css_parameter(xml)
    xml = _lowercase_property_names(xml)
    xml = re.sub(r"<sld:ElseFilter[^>]*/>", "<sld:ElseFilter/>", xml)
    xml = re.sub(r"<sld:Name>\s*</sld:Name>", "", xml)
    return xml
