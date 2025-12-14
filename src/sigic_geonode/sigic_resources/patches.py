import logging

from geonode.base.api.views import ResourceBaseViewSet
from rest_framework.response import Response

from .utils import filter_by_extension, filter_by_geometry, simplify_resource

logger = logging.getLogger(__name__)

# Evita aplicar el parche dos veces
if not getattr(ResourceBaseViewSet, "_patched_by_monkey", False):
    _orig_get_queryset = ResourceBaseViewSet.get_queryset
    _orig_list = ResourceBaseViewSet.list

    def custom_get_queryset(self):
        """
        Devuelve un queryset personalizado para el endpoint /api/v2/resources, aplicando filtros
        adicionales según los parámetros de consulta proporcionados por el usuario:

        - institution: filtra por el campo 'attribution' del recurso.
        - year: filtra por el prefijo del campo 'date'.
        - category: filtra por el identificador de la categoría.
        - keywords / keywords_csv: filtra por palabras clave, con lógica AND (modo=all) o OR (modo=any).

        Si no se proporciona ningún parámetro especial, se comporta como el método original de GeoNode.
        """
        try:
            logger.debug("🚀🚀 custom_get_queryset ejecutado")

            qs = _orig_get_queryset(self)
            req = self.request

            institution = req.query_params.get("institution")
            year = req.query_params.get("year")
            category = req.query_params.get("category")
            keywords = req.query_params.getlist("keywords")

            if institution:
                qs = qs.filter(attribution__iexact=institution)
            if year:
                qs = qs.filter(date__startswith=year)

            if category:
                qs = qs.filter(category__identifier__iexact=category)

            if not keywords:
                csv = req.query_params.get("keywords_csv")
                if csv:
                    keywords = [k.strip() for k in csv.split(",") if k.strip()]
            if keywords:
                mode = (req.query_params.get("keywords_mode") or "any").lower()
                if mode == "all":
                    # Debe contener TODAS las keywords indicadas  (es un and)
                    for kw in keywords:
                        qs = qs.filter(keywords__name__iexact=kw)
                else:
                    # ANY (intersección no vacía)
                    qs = qs.filter(keywords__name__in=keywords).distinct()
            return qs
        except Exception as e:
            logger.warning(f"🚨🚨 Error en custom_get_queryset: {e}")
            return _orig_get_queryset(self)

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

        # Si no piden custom, responde como siempre
        if request.query_params.get("custom", "").lower() != "true":
            return _orig_list(self, request, *args, **kwargs)

        logger.debug("🚀🚀 custom_list ejecutado")
        # Aquí  GeoNode SERIALIZA primero para tener dicts json´s manejables
        resp = _orig_list(self, request, *args, **kwargs)
        data = resp.data  # dict con links/total/... + 'resources' (lista)
        items = data.get("resources") or data.get("results") or []

        # filtrado por extensiones:
        extensions = request.query_params.getlist("file_extension")
        if extensions:
            items = filter_by_extension(items, extensions)

        # filtrado por geometría
        if request.query_params.get("extent_ne") == "[-1,-1,0,0]":
            items = filter_by_geometry(items)

        simplified = [simplify_resource(res) for res in items]

        # Conserva paginación/links y reemplaza la lista
        if isinstance(data, dict) and "resources" in data:
            new_payload = dict(data)
            new_payload["resources"] = simplified
            new_payload["total"] = len(simplified)
            return Response(new_payload)

        return Response(simplified)

    # Inyectamos las funcionalidades a ResourceBaseViewSet
    ResourceBaseViewSet.get_queryset = custom_get_queryset
    ResourceBaseViewSet.list = custom_list
    ResourceBaseViewSet._patched_by_monkey = True
