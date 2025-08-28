import logging
logger = logging.getLogger(__name__)

def simplify_resource(res):
    """Devuelve un diccionario simplificado para armar una respuesta personalizada 
    de un recurso de GeoNode."""
    try:
        return {
            "alternate":   res.get("alternate", ""),
            "abstract":    res.get("abstract", ""),
            "attribution": res.get("attribution", ""),
            "extent":      res.get("extent", {}),
            "embed_url":   res.get("embed_url", ""),
            "uuid":        res.get("uuid", ""),
            "title":       res.get("title", ""),
            "is_approved": res.get("is_approved", False),
            "category":    res.get("category", {}),
        }
    except Exception as e:
        logger.exception(f'❌ Ocurrió el siguiente error en simplify_resource: {e}')
        return {}

def has_geometry(resource_dict):
    """
    Devuelve True si el recurso tiene geometría válida (extent.coords  != [-1,-1,0,0])
    """
    try:
        coords = (
            resource_dict.get("extent", {})
            .get("coords", [])
        )
        return coords != [-1, -1, 0, 0]
    except Exception as e:
        logger.exception(f"❌ Ocurrió el siguiente error en has_geometry: {e}")
        return False
    
def filter_by_geometry(items):
    """Filtra recursos que sí tienen geometría."""
    try:
        return [res for res in items if has_geometry(res)]
    except Exception as e:
        logger.warning(f"❌ Error filtrando por geometría: {e}")
        return items
    
def filter_by_extension(items, requested_ext):
    """Filtra recursos por extensión (e.g., pdf, txt, etc.)"""
    try:
        ext = requested_ext.lower()
        return [
            res for res in items
            if any(link.get("extension", "").lower() == ext for link in res.get("links", []))
        ]
    except Exception as e:
        logger.warning(f"❌ Error filtrando por extensión: {e}")
        return items

