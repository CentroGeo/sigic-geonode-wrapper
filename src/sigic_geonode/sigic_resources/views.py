from geonode.base.api.views import ResourceBaseViewSet

from .filters import MultiWordSearchFilter, SigicFilters, SigicOrderingFilter
from .serializers import SigicResourceShortSerializer


class SigicResourceBaseViewSet(ResourceBaseViewSet):
    """
    Extiende ResourceBaseViewSet con filtros personalizados Sigic. En esta clase se
    mantienen los backends nativos de Geonode  y los personalizados, en los cuales
    es importantes saber:
    - En el SigicFilters usamos `pop()` para consumir únicamente nuestros filtros
    custom (institution, year, has_geometry, extension).
    - Esto evita que DynamicFilterBackend intente procesarlos y marque error:
    "Invalid filter field".
    - Así se logra un "arreglo" entre los dos backs:
    - Los filtros nativos de GeoNode siguen funcionando (ej: category.identifier).
    - Los filtros custom se procesan optimizados, ya que son operaciones directas en BD."""

    filter_backends = [
        SigicFilters,
        MultiWordSearchFilter,
        SigicOrderingFilter,
    ] + ResourceBaseViewSet.filter_backends


class SigicResourceShortViewSet(SigicResourceBaseViewSet):
    """
    Vista reducida con menos campos en la respuesta.
    Reutiliza los filtros optimizados de SigicResourceBaseViewSet.
    """

    serializer_class = SigicResourceShortSerializer
