import logging

from django.contrib.gis.geos import Polygon
from django.db.models import Case, CharField, Exists, F, Q, Value, When
from django.db.models.expressions import Func, OrderBy, OuterRef
from django.db.models.functions import Lower
from geonode.base.models import Link
from rest_framework.filters import BaseFilterBackend, SearchFilter

logger = logging.getLogger(__name__)

WORLD_BBOX = Polygon.from_bbox((-1, -1, 0, 0))


class SigicFilters(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        try:
            institutions = request.query_params.pop("filter{institution}", [])
            years = request.query_params.pop("filter{year}", [])
            has_geometry = request.query_params.pop("filter{has_geometry}", [None])[0]
            extensions = request.query_params.pop("filter{extension}", [])
            complete_metadata = request.query_params.pop(
                "filter{complete_metadata}", [None]
            )[0]

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
            # Se valida la completitud de metadatos
            if complete_metadata is not None:
                if complete_metadata.lower() == "true":
                    queryset = queryset.filter(
                        ~Q(abstract__isnull=True),
                        ~Q(abstract__exact=""),
                        ~Q(abstract__icontains="no abstract provided"),
                        ~Q(category__isnull=True),
                        ~Q(keywords__isnull=True),
                    )
                elif complete_metadata.lower() == "false":
                    queryset = queryset.filter(
                        Q(abstract__isnull=True)
                        | Q(abstract__exact="")
                        | Q(abstract__icontains="no abstract provided")
                        | Q(category__isnull=True)
                        | Q(keywords__isnull=True)
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


class MultiWordSearchFilter(SearchFilter):
    """
    Búsqueda multi-palabra (modo OR), insensible a mayúsculas y acentos.
    No considera entidades HTML porque los textos están guardados correctamente, ya que
    la edición de metadatos se hace desde la interfaz de SIGIC.
    """

    def filter_queryset(self, request, queryset, view):
        # se copian y depuran parámetros de request, pues al parecer el objeto origonal no se puede
        # modificar
        raw = request._request.GET.copy()
        search_terms = raw.pop(self.search_param, [])
        search_fields = raw.pop("search_fields", []) or getattr(
            view, "search_fields", []
        )

        # Evitamos doble reprocesamiento por otros backends
        request._request.GET = raw

        if not search_terms or not search_fields:
            return queryset

        # Creamos anotaciones normalizadas (minúsculas y sin acentos)
        annotations = {f"{f}_u": Unaccent(Lower(F(f))) for f in search_fields}
        queryset = queryset.annotate(**annotations)

        # En esta parte se construye el filtro or
        q = Q()
        for raw_term in search_terms:
            term = raw_term.strip().lower()
            if not term:
                continue

            # se hace la comparación contra cada campo anotado
            for f in search_fields:
                q |= Q(**{f"{f}_u__icontains": term})

        return queryset.filter(q).distinct()


class SigicOrderingFilter(BaseFilterBackend):
    """
    Filtro de ordenamiento SIGIC.
    Solo acepta el parámetro `sort[]` (como en la interfaz de GeoNode).

    Ejemplo:
        ?sort[]=title
        ?sort[]=-title
        ?sort[]=category
        ?sort[]=-category

     Extensión:
        - Soporte de ordenamiento alfabético por categoría en español,
          usando un diccionario de traducciones equivalentes
          al catálogo del frontend de SIGIC.
    """

    # Diccionario estático inglés → español adoh con la UI
    CATEGORY_TRANSLATIONS = {
        "biota": "Biota",
        "boundaries": "Fronteras",
        "climatologyMeteorologyAtmosphere": "Climatología, meteorología y atmósfera",
        "economy": "Economía",
        "elevation": "Elevación",
        "environment": "Medio ambiente",
        "farming": "Agricultura",
        "geoscientificInformation": "Información geocientífica",
        "health": "Salud",
        "imageryBaseMapsEarthCover": "Mapas Base y Cobertura Terrestre",
        "inlandWaters": "Aguas continentales",
        "intelligenceMilitary": "Inteligencia Militar",
        "location": "Ubicación",
        "oceans": "Océanos",
        "planningCadastre": "Planeación Catastral",
        "population": "Población",
        "society": "Sociedad",
        "structure": "Estructura",
        "transportation": "Transporte",
        "utilitiesCommunication": "Servicios Públicos y Comunicación",
    }

    def _norm(self, expr):
        """Normaliza: minúsculas y sin acentos (para orden alfabético natural)."""
        return Lower(Unaccent(expr))

    def filter_queryset(self, request, queryset, view):
        try:
            raw = request._request.GET.copy()
            sort_params = raw.pop("sort[]", [])
            request._request.GET = raw  # Evita reprocesamiento

            if not sort_params:
                logger.debug("SigicOrderingFilter: sin sort[].")
                return queryset

            logger.debug(f"SigicOrderingFilter: sort_params={sort_params}")

            annotations = {}
            ordering = []

            for idx, raw_field in enumerate(sort_params):
                desc = raw_field.startswith("-")
                field = raw_field.lstrip("-")

                # Ordenamiento alfabético (title)
                if field == "title":
                    alias = f"__ord_title_{idx}"
                    annotations[alias] = self._norm(F("title"))
                    ordering.append(OrderBy(F(alias), descending=desc))

                # Ordenamiento semántico en español (category)
                elif field == "category":
                    alias = f"__ord_category_{idx}"

                    # Construimos casos con traducciones
                    whens = [
                        When(category__identifier=k, then=Value(v))
                        for k, v in self.CATEGORY_TRANSLATIONS.items()
                    ]

                    # Anotamos campo temporal con traducción normalizada
                    queryset = queryset.annotate(
                        **{
                            alias: Unaccent(
                                Lower(
                                    Case(
                                        *whens,
                                        default=F("category__identifier"),
                                        output_field=CharField(),
                                    )
                                )
                            )
                        }
                    )

                    ordering.append(OrderBy(F(alias), descending=desc))
                    logger.debug(
                        f"SigicOrderingFilter: aplicado sort por categoría (español, alias={alias})."
                    )

                else:
                    logger.debug(
                        f"SigicOrderingFilter: campo '{field}' no soportado, ignorado."
                    )
                    continue

            # Aplicamos anotaciones globales (solo si las hay)
            if annotations:
                queryset = queryset.annotate(**annotations)

            # 🔚 Orden final
            return queryset.order_by(*ordering)

        except Exception as e:
            logger.warning(f"⚠️ Error en SigicOrderingFilter: {e}")
            return queryset
