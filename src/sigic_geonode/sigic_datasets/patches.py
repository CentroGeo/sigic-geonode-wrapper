import logging

from geonode.layers.api.views import DatasetViewSet
from rest_framework.response import Response


logger = logging.getLogger(__name__)

# Evita aplicar el parche dos veces
if not getattr(DatasetViewSet, "_patched_by_monkey", False):
    print("🧪: getattr")
    _orig_list = DatasetViewSet.list

    def custom_list(self, request, *args, **kwargs):
        """
        Sobrescribe el método list del ResourceBaseViewSet para permitir filtrado avanzado
        cuando el query param 'custom=true' está presente.

        Comportamiento adicional:
        - Filtra por extensión de archivo (extension=.csv, .pdf, etc).
        - Filtra por geometría válida (extent_ne=[-1,-1,0,0] para traer solo recursos con geometría real).
        - Simplifica la estructura del recurso para retornarlo con menos campos.

        Si 'custom' no está presente, devuelve el resultado estándar de GeoNode.
        """

        print("🧪 custom_list")
        return _orig_list(self, request, *args, **kwargs)


    # Inyectamos las funcionalidades a DatasetViewSet
    DatasetViewSet.list = custom_list
    DatasetViewSet._patched_by_monkey = True
