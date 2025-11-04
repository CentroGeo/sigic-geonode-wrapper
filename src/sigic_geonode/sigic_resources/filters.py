# from .lookups import UnaccentIContains
# from . import lookups  # importa para registrar los lookups al arrancar
# import html
import logging

# import re
from typing import Iterable

from django.contrib.gis.geos import Polygon
from django.db.models import Exists, F, OuterRef, Q
from django.db.models.expressions import Func
from django.db.models.functions import Lower
from geonode.base.models import Link
from rest_framework.filters import BaseFilterBackend, SearchFilter

# import unicodedata


logger = logging.getLogger(__name__)

WORLD_BBOX = Polygon.from_bbox((-1, -1, 0, 0))


class SigicFilters(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        try:
            institutions = request.query_params.pop("filter{institution}", [])
            years = request.query_params.pop("filter{year}", [])
            has_geometry = request.query_params.pop("filter{has_geometry}", [None])[0]
            extensions = request.query_params.pop("filter{extension}", [])

            # Diccionario para filtros simples (ej. year,has_ext)
            filters = {}
            if years:
                filters["date__year__in"] = [int(y) for y in years if y.isdigit()]
            if extensions:
                queryset = queryset.annotate(
                    has_ext=Exists(
                        Link.objects.filter(
                            resource=OuterRef("pk"),
                            extension__in=[ext.lower() for ext in extensions],
                        )
                    )
                )
                filters["has_ext"] = True

            # Aquí aplicamos filtros simples (year, has_ext):
            if filters:
                queryset = queryset.filter(**filters)

            if institutions:
                institution_filter = Q()
                for inst in institutions:
                    institution_filter |= Q(attribution__iexact=inst.strip())
                queryset = queryset.filter(institution_filter)
            if has_geometry is not None:
                if has_geometry.lower() == "true":
                    queryset = queryset.exclude(
                        bbox_polygon=WORLD_BBOX,
                        ll_bbox_polygon=WORLD_BBOX,
                    )

            return queryset

        except Exception as e:
            logger.warning(
                f"🚨 Error en el back SigicFilters, en la función filter_queryset: {e}"
            )
            return queryset


class Unaccent(Func):
    """Función PostgreSQL que elimina acentos para búsquedas insensibles."""

    function = "unaccent"
    template = "%(function)s(%(expressions)s)"


# _HTML_ENTITY_MAP = {
#     "á": "&aacute;",  "é": "&eacute;",  "í": "&iacute;",
#     "ó": "&oacute;",  "ú": "&uacute;",  "ñ": "&ntilde;",
#     "Á": "&Aacute;",  "É": "&Eacute;",  "Í": "&Iacute;",
#     "Ó": "&Oacute;",  "Ú": "&Uacute;",  "Ñ": "&Ntilde;",
#     "ü": "&uuml;",    "Ü": "&Uuml;",
# }


# def to_html_entities(s: str) -> str:
#     """Convierte letras acentuadas y ñ/ü a entidades HTML (&oacute;, &ntilde;, etc.)."""
#     r = s
#     for ch, ent in _HTML_ENTITY_MAP.items():
#         r = r.replace(ch, ent)
#     return r


# def normalize_term(term: str) -> str:
#     """Recorta/minúsculas y decodifica entidades HTML si el usuario las mandó (&oacute;)."""
#     t = term.strip().lower()
#     if "&" in t and ";" in t:
#         t = html.unescape(t)
#     return t


# def strip_accents_py(s: str) -> str:
#     """Quita acentos en Python (útil para comparar contra variantes des–entidadizadas)."""
#     return "".join(
#         c for c in unicodedata.normalize("NFD", s)
#         if unicodedata.category(c) != "Mn"
#     )


# class MultiWordSearchFilter(SearchFilter):
#     """
#     Búsqueda multi-palabra (OR), insensible a mayúsculas y acentos,
#     y compatible con contenidos guardados con entidades HTML (&oacute;, &ntilde;, …).
#     Soporta múltiples ?search=… y múltiples ?search_fields=…
#     """

#     def filter_queryset(self, request, queryset, view):
#         raw = request._request.GET.copy()

#         # Lee todas las ocurrencias
#         raw_terms: Iterable[str] = raw.getlist(self.search_param)
#         raw_fields: Iterable[str] = raw.getlist("search_fields")

#         # Si no mandan search_fields, usa los de la vista
#         search_fields = [f.strip() for f in (raw_fields or getattr(view, "search_fields", [])
#  or []) if f and f.strip()]
#         search_terms = [t for t in (raw_terms or []) if t and t.strip()]

#         # Evita reproceso por otros backends
#         for k in (self.search_param, "search_fields"):
#             if k in raw:
#                 raw.pop(k)
#         request._request.GET = raw

#         if not search_terms or not search_fields:
#             return queryset

#         # --- Anotaciones por campo ---
#         annotations = {}
#         for f in search_fields:
#             annotations[f"{f}_u"] = Unaccent(Lower(F(f)))

#             # Construimos una cadena de Replace para convertir entidades a letras sin acento
#             expr = F(f)
#             ent2plain = {
#                 "&aacute;": "a", "&eacute;": "e", "&iacute;": "i",
#                 "&oacute;": "o", "&uacute;": "u", "&ntilde;": "n",
#                 "&uuml;": "u",
#                 "&Aacute;": "a", "&Eacute;": "e", "&Iacute;": "i",
#                 "&Oacute;": "o", "&Uacute;": "u", "&Ntilde;": "n",
#                 "&Uuml;": "u",
#             }
#             for ent, plain in ent2plain.items():
#                 expr = Replace(expr, Value(ent), Value(plain), output_field=TextField())
#             annotations[f"{f}_de"] = Lower(expr)

#         queryset = queryset.annotate(**annotations)

#         # --- Construir el OR global ---
#         q = Q()
#         for raw_term in search_terms:
#             t_unicode = normalize_term(raw_term)         # "investigación" o "investigacion"
#             if not t_unicode:
#                 continue
#             t_noaccent = strip_accents_py(t_unicode)     # "investigacion"
#             t_entities = to_html_entities(t_unicode)     # "investigaci&oacute;n"

#             for f in search_fields:
#                 # 1) Texto unicode en BD -> comparar contra término SIN acento
#                 q |= Q(**{f"{f}_u__icontains": t_noaccent})

#                 # 2) Texto con entidades y usuario escribe CON acento -> busca la entidad
#                 q |= Q(**{f"{f}__icontains": t_entities})

#                 # 3) Texto con entidades y usuario escribe SIN acento -> compara en *_de
#                 q |= Q(**{f"{f}_de__icontains": t_noaccent})

#         return queryset.filter(q).distinct()

# =========================================================
class MultiWordSearchFilter(SearchFilter):
    """
    Búsqueda multi-palabra (modo OR), insensible a mayúsculas y acentos.
    No considera entidades HTML porque los textos están guardados correctamente.
    """

    def filter_queryset(self, request, queryset, view):
        raw = request._request.GET.copy()

        # Ejemplo: ?search=agua&search=infraestructura
        search_terms: Iterable[str] = raw.pop(self.search_param, [])
        # Ejemplo: ?search_fields=title&search_fields=abstract
        search_fields: Iterable[str] = raw.pop("search_fields", []) or getattr(
            view, "search_fields", []
        )

        # Evitar reprocesamiento por otros backends
        request._request.GET = raw

        if not search_terms or not search_fields:
            return queryset

        # Crear anotaciones normalizadas (minúsculas y sin acentos)
        annotations = {f"{f}_u": Unaccent(Lower(F(f))) for f in search_fields}
        queryset = queryset.annotate(**annotations)

        q = Q()
        for raw_term in search_terms:
            term = raw_term.strip().lower()
            if not term:
                continue

            # Comparar contra cada campo anotado
            for f in search_fields:
                q |= Q(**{f"{f}_u__icontains": term})

        return queryset.filter(q).distinct()
