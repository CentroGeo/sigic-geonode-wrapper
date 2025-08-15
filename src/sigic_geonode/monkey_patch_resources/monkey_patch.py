from geonode.base.api.views import ResourceBaseViewSet
from rest_framework.response import Response

# Evita aplicar el parche dos veces
if not getattr(ResourceBaseViewSet, "_patched_by_monkey", False):
    _orig_get_queryset = ResourceBaseViewSet.get_queryset
    _orig_list = ResourceBaseViewSet.list

    def custom_get_queryset(self):
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

    def custom_list(self, request, *args, **kwargs):
        # Si no piden custom, responde como siempre
        if request.query_params.get("custom", "").lower() != "true":
            return _orig_list(self, request, *args, **kwargs)

        # Aquí  GeoNode SERIALIZA primero para tener dicts json´s manejables
        resp = _orig_list(self, request, *args, **kwargs)
        data = resp.data  # dict con links/total/... + 'resources' (lista)
        items = data.get("resources") or data.get("results") or []

        simplified = []
        for res in items:
            simplified.append({
                "alternate":   res.get("alternate", ""),
                "abstract":    res.get("abstract", ""),
                "attribution": res.get("attribution", ""),
                "extent":      res.get("extent", {}),
                "embed_url":   res.get("embed_url", ""),
                "uuid":        res.get("uuid", ""),
                "title":       res.get("title", ""),
                "is_approved": res.get("is_approved", False),
                "category":    res.get("category", {}),
            })

        # Conserva paginación/links y reemplaza la lista
        if isinstance(data, dict) and "resources" in data:
            new_payload = dict(data)
            new_payload["resources"] = simplified
            return Response(new_payload)

        return Response(simplified)
    
    # Inyectamos las funcionalidades a ResourceBaseViewSet
    ResourceBaseViewSet.get_queryset = custom_get_queryset
    ResourceBaseViewSet.list = custom_list
    ResourceBaseViewSet._patched_by_monkey = True
