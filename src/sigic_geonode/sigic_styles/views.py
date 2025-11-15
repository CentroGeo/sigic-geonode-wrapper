from geonode.layers.api.views import DatasetViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
import requests

GEOSERVER_BASE_URL = settings.OGC_SERVER["default"]["LOCATION"]

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
            "default_style": default_style,
            "styles": associated_styles,
        })

    @action(
        detail=True,
        methods=["get"],
        url_path=r"styles/(?P<style_name>[^/]+)"
    )
    def get_style(self, request, pk=None, style_name=None):
        dataset = self.get_object()

        gs = settings.OGC_SERVER["default"]
        gs_url = gs["LOCATION"].rstrip("/")
        auth = (gs["USER"], gs["PASSWORD"])

        # detectar si pidió .sld
        path = request.get_full_path()
        wants_download = path.endswith(".sld")

        # limpiar .sld si viene incluido
        if style_name.lower().endswith(".sld"):
            style_name = style_name[:-4]

        # workspace de la capa
        layer_name = dataset.alternate  # ej. geonode:mexreg1
        workspace = layer_name.split(":")[0]  # ej. geonode

        # --- 1) buscar en workspace ---
        ws_url = f"{gs_url}/rest/workspaces/{workspace}/styles/{style_name}.sld"
        r = requests.get(ws_url, auth=auth)

        # --- 2) si no existe, intentar global ---
        if r.status_code == 404:
            global_url = f"{gs_url}/rest/styles/{style_name}.sld"
            r = requests.get(global_url, auth=auth)

        if r.status_code != 200:
            return Response(
                {"detail": f"Style '{style_name}' not found in workspace '{workspace}' or globally"},
                status=404
            )

        content = r.content

        # VISUALIZACIÓN
        if not wants_download:
            return HttpResponse(content, content_type="text/xml")

        # DESCARGA
        response = HttpResponse(
            content,
            content_type="application/vnd.ogc.sld+xml"
        )
        response["Content-Disposition"] = f'attachment; filename="{style_name}.sld"'
        return response
