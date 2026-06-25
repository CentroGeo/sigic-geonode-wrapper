# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

"""
Parsers de metadatos para importación desde archivos XML estándar.

Formatos soportados:
- ISO 19139 (metadatos geoespaciales)
- Dublin Core XML (metadatos genéricos)

Los campos retornados usan los mismos nombres que el store editedMetadata.js
del frontend, para que el mapping sea directo.
"""

import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

_NS_ISO = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml",
    "srv": "http://www.isotc211.org/2005/srv",
    "xlink": "http://www.w3.org/1999/xlink",
}

_NS_DC = {
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

# Topic categories ISO 19115 → GeoNode identifier
_TOPIC_CATEGORY_MAP = {
    "farming": "farming",
    "biota": "biota",
    "boundaries": "boundaries",
    "climatologyMeteorologyAtmosphere": "climatologyMeteorologyAtmosphere",
    "economy": "economy",
    "elevation": "elevation",
    "environment": "environment",
    "geoscientificInformation": "geoscientificInformation",
    "health": "health",
    "imageryBaseMapsEarthCover": "imageryBaseMapsEarthCover",
    "intelligenceMilitary": "intelligenceMilitary",
    "inlandWaters": "inlandWaters",
    "location": "location",
    "oceans": "oceans",
    "planningCadastre": "planningCadastre",
    "society": "society",
    "structure": "structure",
    "transportation": "transportation",
    "utilitiesCommunication": "utilitiesCommunication",
}

# Date type normalization
_DATE_TYPE_MAP = {
    "creation": "creation",
    "publication": "publication",
    "revision": "revision",
}

# Maintenance frequency normalization
_FREQUENCY_MAP = {
    "continual": "continual",
    "daily": "daily",
    "weekly": "weekly",
    "fortnightly": "fortnightly",
    "monthly": "monthly",
    "quarterly": "quarterly",
    "biannually": "biannually",
    "annually": "annually",
    "asNeeded": "asNeeded",
    "irregular": "irregular",
    "notPlanned": "notPlanned",
    "unknown": "unknown",
}


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(xml_bytes: bytes) -> str:
    """
    Detecta el formato del XML de metadatos.

    Retorna: 'iso19139' | 'dublin_core' | 'fgdc' | 'unknown'
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return "unknown"

    tag = root.tag
    if "MD_Metadata" in tag or "www.isotc211.org/2005/gmd" in tag:
        return "iso19139"
    if "oai_dc" in tag or "purl.org/dc" in tag:
        return "dublin_core"
    # FGDC: root <metadata> sin namespace con hijo <idinfo>
    if tag == "metadata" and root.find("idinfo") is not None:
        return "fgdc"

    # Buscar en children por si el root es un envelope
    for child in root:
        if "MD_Metadata" in child.tag or "www.isotc211.org/2005/gmd" in child.tag:
            return "iso19139"
        if "oai_dc" in child.tag or "purl.org/dc" in child.tag:
            return "dublin_core"

    # Fallback: buscar por string en el contenido raw
    content = xml_bytes.decode("utf-8", errors="ignore")
    if "www.isotc211.org/2005/gmd" in content or "MD_Metadata" in content:
        return "iso19139"
    if "purl.org/dc/elements" in content or "oai_dc" in content:
        return "dublin_core"
    if "FGDC-STD" in content or ("idinfo" in content and "citeinfo" in content):
        return "fgdc"

    return "unknown"


# ---------------------------------------------------------------------------
# ISO 19139 parser
# ---------------------------------------------------------------------------

def _text(element):
    """Retorna el texto de un elemento, o None si es None."""
    if element is not None:
        t = element.text
        if t:
            return t.strip() or None
    return None


def _attrib(element, attr):
    """Retorna un atributo de un elemento, o None si el elemento es None."""
    if element is not None:
        val = element.attrib.get(attr, "").strip()
        return val or None
    return None


def parse_iso19139(xml_bytes: bytes) -> dict:
    """
    Parsea un archivo ISO 19139 y retorna un dict con los campos del store.

    Solo incluye en el dict los campos que tienen valor.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"XML inválido: {e}")

    ns = _NS_ISO
    fields = {}

    # --- identificationInfo ---
    id_info = root.find(".//gmd:identificationInfo/gmd:MD_DataIdentification", ns)
    if id_info is None:
        # intento alternativo para SVIdentification
        id_info = root.find(".//gmd:identificationInfo/srv:SV_ServiceIdentification", ns)

    if id_info is not None:
        # title
        title = _text(id_info.find(
            "gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString", ns
        ))
        if title:
            fields["title"] = title

        # abstract
        abstract = _text(id_info.find("gmd:abstract/gco:CharacterString", ns))
        if abstract:
            fields["abstract"] = abstract

        # purpose
        purpose = _text(id_info.find("gmd:purpose/gco:CharacterString", ns))
        if purpose:
            fields["purpose"] = purpose

        # supplemental_information
        supp = _text(id_info.find("gmd:supplementalInformation/gco:CharacterString", ns))
        if supp:
            fields["supplemental_information"] = supp

        # edition
        edition = _text(
            id_info.find(
                "gmd:citation/gmd:CI_Citation/gmd:edition/gco:CharacterString", ns
            )
        )
        if edition:
            fields["edition"] = edition

        # date + date_type (tomamos la primera fecha disponible)
        for ci_date in id_info.findall(
            "gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date", ns
        ):
            date_val = _text(ci_date.find("gmd:date/gco:Date", ns))
            if not date_val:
                date_val = _text(ci_date.find("gmd:date/gco:DateTime", ns))
            date_type_el = ci_date.find(
                "gmd:dateType/gmd:CI_DateTypeCode", ns
            )
            date_type_raw = (
                _attrib(date_type_el, "codeListValue")
                or _text(date_type_el)
                or ""
            ).lower()
            date_type = _DATE_TYPE_MAP.get(date_type_raw, "publication")
            if date_val:
                # normalizar a YYYY-MM-DD
                fields["date"] = date_val[:10]
                fields["date_type"] = date_type
                break

        # language
        lang_el = id_info.find(
            "gmd:language/gmd:LanguageCode", ns
        )
        lang = (
            _attrib(lang_el, "codeListValue")
            or _text(lang_el)
        )
        if lang:
            fields["language"] = lang.lower()

        # category (topicCategory)
        topic = _text(
            id_info.find("gmd:topicCategory/gmd:MD_TopicCategoryCode", ns)
        )
        if topic and topic in _TOPIC_CATEGORY_MAP:
            fields["category"] = _TOPIC_CATEGORY_MAP[topic]

        # keywords
        keywords = []
        for kw_el in id_info.findall(
            ".//gmd:MD_Keywords/gmd:keyword/gco:CharacterString", ns
        ):
            kw = _text(kw_el)
            if kw:
                keywords.append(kw)
        if keywords:
            fields["keywords"] = ", ".join(keywords)

        # DOI — buscar en identifier
        for id_el in id_info.findall(
            "gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString",
            ns,
        ):
            val = _text(id_el)
            if val and ("doi" in val.lower() or "10." in val):
                # limpiar URI doi.org si es necesario
                if val.startswith("https://doi.org/"):
                    val = val[len("https://doi.org/"):]
                elif val.startswith("http://doi.org/"):
                    val = val[len("http://doi.org/"):]
                elif val.lower().startswith("doi:"):
                    val = val[4:]
                fields["doi"] = val
                break

        # restrictions
        for constraints in id_info.findall(
            ".//gmd:MD_LegalConstraints", ns
        ):
            # restriction_code_type
            access_code = constraints.find(
                "gmd:accessConstraints/gmd:MD_RestrictionCode", ns
            )
            code_val = _attrib(access_code, "codeListValue") or _text(access_code)
            if code_val and "restriction_code_type" not in fields:
                fields["restriction_code_type"] = code_val

            # constraints_other
            other = _text(
                constraints.find("gmd:otherConstraints/gco:CharacterString", ns)
            )
            if other and "constraints_other" not in fields:
                fields["constraints_other"] = other

        # maintenance_frequency
        freq_el = id_info.find(
            ".//gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode",
            ns,
        )
        freq = _attrib(freq_el, "codeListValue") or _text(freq_el)
        if freq and freq in _FREQUENCY_MAP:
            fields["maintenance_frequency"] = _FREQUENCY_MAP[freq]

    # --- root-level: language fallback ---
    if "language" not in fields:
        lang_el = root.find("gmd:language/gmd:LanguageCode", ns)
        lang = _attrib(lang_el, "codeListValue") or _text(lang_el)
        if lang:
            fields["language"] = lang.lower()

    # --- contact: attribution ---
    for contact_el in root.findall(".//gmd:CI_ResponsibleParty", ns):
        org = _text(contact_el.find("gmd:organisationName/gco:CharacterString", ns))
        if org and "attribution" not in fields:
            fields["attribution"] = org
            break

    # --- dataQualityInfo: data_quality_statement ---
    dq_stmt = _text(
        root.find(
            ".//gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement/gco:CharacterString",
            ns,
        )
    )
    if dq_stmt:
        fields["data_quality_statement"] = dq_stmt

    return fields


# ---------------------------------------------------------------------------
# Dublin Core parser
# ---------------------------------------------------------------------------

def parse_dublin_core(xml_bytes: bytes) -> dict:
    """
    Parsea un archivo Dublin Core XML y retorna un dict con los campos del store.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"XML inválido: {e}")

    ns = _NS_DC
    fields = {}

    def _find_dc(tag):
        """Busca un elemento dc:tag en el árbol."""
        # Con namespace explícito
        el = root.find(f"dc:{tag}", ns)
        if el is None:
            # Sin namespace (Dublin Core simple)
            el = root.find(tag)
        return _text(el)

    def _findall_dc(tag):
        """Busca todos los elementos dc:tag."""
        els = root.findall(f"dc:{tag}", ns)
        if not els:
            els = root.findall(tag)
        return [_text(e) for e in els if _text(e)]

    # title
    title = _find_dc("title")
    if title:
        fields["title"] = title

    # abstract
    abstract = _find_dc("description")
    if abstract:
        fields["abstract"] = abstract

    # keywords (todos los dc:subject)
    subjects = _findall_dc("subject")
    if subjects:
        fields["keywords"] = ", ".join(subjects)

    # language
    lang = _find_dc("language")
    if lang:
        fields["language"] = lang.lower()[:3]  # normalizar a código de 3 letras si es largo

    # date
    date_val = _find_dc("date")
    if date_val:
        fields["date"] = date_val[:10]
        fields["date_type"] = "publication"

    # attribution (creator o publisher)
    creator = _find_dc("creator") or _find_dc("publisher")
    if creator:
        fields["attribution"] = creator

    # constraints_other (rights)
    rights = _find_dc("rights")
    if rights:
        fields["constraints_other"] = rights

    # doi (identifier que contenga doi)
    identifiers = _findall_dc("identifier")
    for ident in identifiers:
        if ident and ("doi" in ident.lower() or "10." in ident):
            val = ident
            if val.startswith("https://doi.org/"):
                val = val[len("https://doi.org/"):]
            elif val.startswith("http://doi.org/"):
                val = val[len("http://doi.org/"):]
            elif val.lower().startswith("doi:"):
                val = val[4:]
            fields["doi"] = val
            break

    return fields


# ---------------------------------------------------------------------------
# FGDC parser
# ---------------------------------------------------------------------------

def _fgdc_text(root, path):
    """Retorna el texto del primer elemento que coincide con la ruta simple."""
    el = root.find(path)
    if el is not None and el.text:
        return el.text.strip() or None
    return None


def _fgdc_date(raw: str) -> str:
    """Normaliza fechas FGDC (YYYYMMDD o YYYY) a YYYY-MM-DD."""
    raw = (raw or "").strip().replace("-", "")
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    if len(raw) == 4 and raw.isdigit():
        return f"{raw}-01-01"
    return raw[:10] if raw else ""


def parse_fgdc(xml_bytes: bytes) -> dict:
    """
    Parsea un archivo FGDC (Content Standards for Digital Geospatial Metadata)
    y retorna un dict con los campos del store editedMetadata.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"XML FGDC inválido: {e}")

    fields = {}

    # title
    title = _fgdc_text(root, "idinfo/citation/citeinfo/title")
    if title:
        fields["title"] = title

    # abstract
    abstract = _fgdc_text(root, "idinfo/descript/abstract")
    if abstract:
        fields["abstract"] = abstract

    # purpose
    purpose = _fgdc_text(root, "idinfo/descript/purpose")
    if purpose:
        fields["purpose"] = purpose

    # supplemental_information
    supplinf = _fgdc_text(root, "idinfo/descript/supplinf")
    if supplinf:
        fields["supplemental_information"] = supplinf

    # attribution / origin
    origin = _fgdc_text(root, "idinfo/citation/citeinfo/origin")
    if origin:
        fields["attribution"] = origin

    # date (pubdate)
    pubdate_raw = _fgdc_text(root, "idinfo/citation/citeinfo/pubdate")
    pubdate = _fgdc_date(pubdate_raw) if pubdate_raw else None
    if pubdate and pubdate not in ("0000-00-00", "00000000"):
        fields["date"] = pubdate
        fields["date_type"] = "publication"

    # keywords — recoger themekey del tema con themekt más genérico (CONABIO)
    keywords = []
    for theme_el in root.findall("idinfo/keywords/theme"):
        themekt = _fgdc_text(theme_el, "themekt") or ""
        if themekt.upper() in ("CONABIO", "ESTRUCTURA", ""):
            for kw_el in theme_el.findall("themekey"):
                kw = (kw_el.text or "").strip()
                if kw and len(kw) < 80:
                    keywords.append(kw)
    if not keywords:
        for kw_el in root.findall("idinfo/keywords/theme/themekey"):
            kw = (kw_el.text or "").strip()
            if kw and len(kw) < 80:
                keywords.append(kw)
    if keywords:
        fields["keywords"] = ", ".join(dict.fromkeys(keywords))

    # constraints
    accconst = _fgdc_text(root, "idinfo/accconst")
    useconst = _fgdc_text(root, "idinfo/useconst")
    constraints_parts = [p for p in [accconst, useconst] if p and p.lower() not in ("none", "ninguno")]
    if constraints_parts:
        fields["constraints_other"] = " | ".join(constraints_parts)

    # data_quality_statement — lineage procstep
    procdesc = _fgdc_text(root, "dataqual/lineage/procstep/procdesc")
    if procdesc:
        fields["data_quality_statement"] = procdesc

    return fields
