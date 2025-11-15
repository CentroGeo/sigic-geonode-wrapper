from geonode.layers.api.views import DatasetViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
from rest_framework.exceptions import NotFound
import requests
import json


class SigicDatasetViewSet(DatasetViewSet):

    @action(detail=True, methods=["get"], url_path="ping")
    def ping(self, request, pk=None):
        return Response({"status": "ok"})

    @action(detail=True, methods=["get"], url_path="styles")
    def list_styles(self, request, pk=None):
        """
        Lista los estilos de GeoServer para esta capa usando REST en JSON.
        """
        dataset = self.get_object()
        layer_name = dataset.alternate

        gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
        auth = (settings.OGC_SERVER["default"]["USER"], settings.OGC_SERVER["default"]["PASSWORD"])

        # --- 1. Estilos asociados ---
        url_styles = f"{gs_url}/rest/layers/{layer_name}/styles.json"
        r_styles = requests.get(url_styles, auth=auth)
        r_styles.raise_for_status()
        styles_data = r_styles.json()

        associated_styles = [
            s["name"] for s in styles_data.get("styles", {}).get("style", [])
        ]

        # --- 2. Estilo por defecto ---
        url_layer = f"{gs_url}/rest/layers/{layer_name}.json"
        r_layer = requests.get(url_layer, auth=auth)
        r_layer.raise_for_status()
        layer_data = r_layer.json()

        default_style = layer_data.get("layer", {}) \
                                  .get("defaultStyle", {}) \
                                  .get("name")

        return Response({
            "layer": layer_name,
            "default_style": default_style.split(":")[-1] if default_style else None,
            "styles": associated_styles,
        })

    @action(detail=True, methods=["get"], url_path=r"styles/(?P<style_name>.+)")
    def get_style(self, request, pk=None, style_name=None):
        dataset = self.get_object()
        layer_name = dataset.alternate
        workspace = layer_name.split(":")[0]

        gs = settings.OGC_SERVER["default"]
        gs_url = gs["LOCATION"].rstrip("/")
        auth = (gs["USER"], gs["PASSWORD"])

        # 1) Obtener estilos asociados reales
        r_styles = requests.get(f"{gs_url}/rest/layers/{layer_name}/styles.json", auth=auth)
        if r_styles.status_code != 200:
            return Response({"detail": "GeoServer error fetching styles"}, status=500)

        styles = r_styles.json().get("styles", {}).get("style", [])
        associated_names = []
        for s in styles:
            name = s.get("name")
            if not name:
                continue
            associated_names.append(name)  # geonode:foo
            if ":" in name:
                associated_names.append(name.split(":")[1])  # foo

        # Default style también cuenta
        r_layer = requests.get(f"{gs_url}/rest/layers/{layer_name}.json", auth=auth)
        if r_layer.status_code == 200:
            default_name = (
                r_layer.json()
                .get("layer", {})
                .get("defaultStyle", {})
                .get("name")
            )
            if default_name:
                associated_names.append(default_name)
                if ":" in default_name:
                    associated_names.append(default_name.split(":")[1])

        # 2) Normalizar el estilo solicitado
        download = style_name.endswith(".sld")
        clean = style_name[:-4] if download else style_name

        # 3) Validar asociación REAL
        if clean not in associated_names:
            return Response(
                {"detail": f"Style '{clean}' is not associated with this dataset"},
                status=404
            )

        # 4) Obtener SLD desde workspace o global
        ws_url = f"{gs_url}/rest/workspaces/{workspace}/styles/{clean}.sld"
        global_url = f"{gs_url}/rest/styles/{clean}.sld"

        r = requests.get(ws_url, auth=auth)
        if r.status_code == 404:
            r = requests.get(global_url, auth=auth)

        if r.status_code == 404:
            return Response({"detail": f"Style '{clean}' not found on GeoServer"}, status=404)

        if r.status_code != 200:
            return Response({"detail": "GeoServer style fetch error"}, status=500)

        # 5) Respuesta final
        sld = r.text
        if download:
            resp = HttpResponse(sld, content_type="application/xml")
            resp["Content-Disposition"] = f'attachment; filename="{clean}.sld"'
            return resp

        return HttpResponse(sld, content_type="application/xml")