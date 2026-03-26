import re


def needs_fix(xml: str) -> bool:
    """Detecta si un SLD requiere corrección (QGIS, SLD 1.1.0, etc.)."""
    return (
        'version="1.1.0"' in xml
        or 'xmlns:se="http://www.opengis.net/se"' in xml
        or bool(re.search(r"\bse:", xml))
        or "SvgParameter" in xml
        or (
            "<StyledLayerDescriptor " in xml
            and "<sld:StyledLayerDescriptor" not in xml
        )
    )


def fix_sld(xml) -> str:
    """
    Normalización completa de SLD para compatibilidad con GeoServer.
    Acepta str o bytes. Retorna str.

    Transformaciones (en orden):
    1. version="1.1.0" → "1.0.0"
    2. xmlns:se → xmlns:sld
    3. <se:*> → <sld:*>  (prefijos de elementos)
    4. Raíz: <StyledLayerDescriptor → <sld:StyledLayerDescriptor
    5. SvgParameter → CssParameter
    6. Agrega xmlns:sld si falta y hay elementos sld:
    7. Corrige xsi:schemaLocation a SLD 1.0.0
    8. Elimina xmlns:ogc redundantes (dentro de nodos hijos)
    9. Elimina xmlns:se residual
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
    xml = re.sub(r"<(/?)se:", r"<\1sld:", xml)
    xml = re.sub(r"<StyledLayerDescriptor\b", "<sld:StyledLayerDescriptor", xml)
    xml = re.sub(r"</StyledLayerDescriptor>", "</sld:StyledLayerDescriptor>", xml)
    xml = xml.replace("SvgParameter", "CssParameter")
    if "sld:" in xml and 'xmlns:sld=' not in xml:
        xml = re.sub(
            r"(<sld:StyledLayerDescriptor\s)",
            r'\1xmlns:sld="http://www.opengis.net/sld" ',
            xml,
        )
    xml = re.sub(
        r'xsi:schemaLocation="[^"]+"',
        'xsi:schemaLocation="http://www.opengis.net/sld '
        'http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd"',
        xml,
    )
    xml = re.sub(r'\s+xmlns:se="[^"]+"', "", xml)
    xml = re.sub(r"<sld:ElseFilter[^>]*/>", "<sld:ElseFilter/>", xml)
    xml = re.sub(r"<sld:Name>\s*</sld:Name>", "", xml)
    return xml
