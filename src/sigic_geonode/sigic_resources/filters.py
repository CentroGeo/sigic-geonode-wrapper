import logging

from django.contrib.gis.geos import Polygon
from django.db.models import Exists, OuterRef, Q
from geonode.base.models import Link
from rest_framework.filters import BaseFilterBackend

logger = logging.getLogger(__name__)

# Bounding box mundial (sin geometría real) se asigna a los documentos pdf de manera gral.
WORLD_BBOX = Polygon.from_bbox((-180, -90, 180, 90))


class SigicFilters(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        try:
            institutions = request.query_params.pop("filter{institution}", [])
            years = request.query_params.pop("filter{year}", [])
            has_geometry = request.query_params.pop("filter{has_geometry}", [None])[0]
            extensions = request.query_params.pop("filter{extension}", [])

            # Diccionario para filtros simples (ej. year,has_ext, resource_type)
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
                filters["resource_type"] = "document"
            # Aquí aplicamos filtros simples (year, has_ext, resource_type):
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
