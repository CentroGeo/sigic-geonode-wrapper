from geonode.base.api.views import ResourceBaseViewSet

from .filters import SigicFilters
from .serializers import SigicResourceShortSerializer


class SigicResourceBaseViewSet(ResourceBaseViewSet):
    """
    Extiende ResourceBaseViewSet con filtros personalizados Sigic."""

    filter_backends = [SigicFilters,] + [
        backend
        for backend in ResourceBaseViewSet.filter_backends
        if backend.__name__ != "DynamicFilterBackend"
        #     En esta parte se quitó el DynamicFilterBackend que trae GeoNode por defecto, ya que no
        #     entiende la sintaxis filter{...} con nuestros filtros personalizados y generaba el error:
        #     {
        #     "success": false,
        #     "errors": [
        #         "Invalid filter field: extension"
        #     ],
        #     "code": "invalid"
        # }
        #     En su lugar, se añade SigicFilters para manejar esos parámetros de forma controlada,
        #     eficiente y homologada con los filtros nativos de Geonode.
    ]


class SigicResourceShortViewSet(SigicResourceBaseViewSet):
    """
    Vista reducida con menos campos en la respuesta.
    Reutiliza los filtros optimizados de SigicResourceBaseViewSet.
    """

    serializer_class = SigicResourceShortSerializer
