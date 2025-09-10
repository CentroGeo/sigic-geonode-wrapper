import logging

logger = logging.getLogger(__name__)


def simplify_resource(res):
    """Devuelve un diccionario simplificado para armar una respuesta personalizada
    de un recurso de GeoNode."""
    try:
        return {
            "alternate": res.get("alternate", ""),
            "abstract": res.get("abstract", ""),
            "attribution": res.get("attribution", ""),
            "extent": res.get("extent", {}),
            "embed_url": res.get("embed_url", ""),
            "uuid": res.get("uuid", ""),
            "title": res.get("title", ""),
            "is_approved": res.get("is_approved", False),
            "category": res.get("category", {}),
            "download_url": res.get("download_url", ""),
            "download_urls": res.get("download_urls", []),
            "keywords": res.get("keywords", []),
            "last_updated": res.get("last_updated", ""),
            "links": res.get("links", []),
            "owner": res.get("owner", {}),
            "pk": res.get("pk", ""),
            "resource_type": res.get("resource_type", ""),
            "sourcetype": res.get("sourcetype", ""),
            "subtype": res.get("subtype", ""),
            "thumbnail_url": res.get("thumbnail_url", ""),
            "raw_abstract": res.get("raw_abstract", ""),
            "srid": res.get("srid", ""),
            "featured": res.get("featured", False),
            "advertised": res.get("advertised", False),
            "is_published": res.get("is_published", False),
            "created": res.get("created", ""),
            "date": res.get("created", ""),
        }
    except Exception as e:
        logger.warning(f"🚨🚨 Ocurrió el siguiente error en simplify_resource: {e}")
        return {}


def has_geometry(resource_dict):
    """
    Devuelve True si el recurso tiene geometría válida (extent.coords  != [-1,-1,0,0])
    """
    try:
        coords = resource_dict.get("extent", {}).get("coords", [])
        return coords != [-1, -1, 0, 0]
    except Exception as e:
        logger.warning(f"🚨🚨 Ocurrió el siguiente error en has_geometry: {e}")
        return False


def filter_by_geometry(items):
    """Filtra recursos que sí tienen geometría."""
    try:
        return [res for res in items if has_geometry(res)]
    except Exception as e:
        logger.warning(f"🚨🚨 Error filtrando por geometría: {e}")
        return items


def filter_by_extension(items, requested_exts):
    """
    Filtra recursos por una o más extensiones (e.g., pdf, txt).
    Aplica lógica OR: al menos una debe coincidir.
    """
    try:
        if isinstance(requested_exts, str):
            ext_list = [requested_exts.lower()]
        else:
            ext_list = [ext.lower() for ext in requested_exts]

        return [
            res
            for res in items
            if any(
                link.get("extension", "").lower() in ext_list
                for link in res.get("links", [])
            )
        ]
    except Exception as e:
        logger.warning(f"🚨🚨 Error filtrando por extensión: {e}")
        return items
