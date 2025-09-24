import logging

from django.contrib.gis.geos import Polygon
from django.db.models import Exists, OuterRef
from geonode.base.models import Link
from rest_framework.filters import BaseFilterBackend

logger = logging.getLogger(__name__)

# Bounding box mundial (sin geometría real) se asigna a los documentos pdf de manera gral.
WORLD_BBOX = Polygon.from_bbox((-180, -90, 180, 90))


class SigicFilters(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        try:
            filters = {}

            institution = request.query_params.get("filter{institution}")
            year = request.query_params.get("filter{year}")
            has_geometry = request.query_params.get("filter{has_geometry}")
            extensions = request.query_params.getlist("filter{extension}")

            if institution:
                filters["attribution__iexact"] = institution
            if year:
                filters["date__year"] = year
            if has_geometry is not None:
                if has_geometry.lower() == "true":
                    queryset = queryset.exclude(
                        bbox_polygon=WORLD_BBOX, ll_bbox_polygon=WORLD_BBOX
                    )
                elif has_geometry.lower() == "false":
                    queryset = queryset.filter(
                        bbox_polygon=WORLD_BBOX, ll_bbox_polygon=WORLD_BBOX
                    )
            if extensions:
                queryset = queryset.annotate(
                    has_ext=Exists(
                        Link.objects.filter(
                            resource=OuterRef("pk"),
                            extension__in=[ext.lower() for ext in extensions],
                        )
                    )
                ).filter(has_ext=True, resource_type="document")
            if filters:
                queryset = queryset.filter(**filters)
            return queryset
        except Exception as e:
            logger.warning(
                f"🚨🚨 Error en el back SigicFilters, en la función filter_queryset : {e}"
            )
            return queryset
