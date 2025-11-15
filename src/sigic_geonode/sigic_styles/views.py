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

    @action(detail=True, methods=["get"], url_path=r"styles/(?P<style_name>[^/]+)")
    def get_style(self, request, pk=None, style_name=None):
        """
        Devuelve el contenido SLD de un estilo asociado a este dataset.
        - /styles/<style> → inline (text/xml)
        - /styles/<style>.sld → descarga
        - Solo estilos asociados → si no, 404
        - Respeta workspace del estilo (ej. geonode)
        """

        dataset = self.get_object()
        layer_name = dataset.alternate  # ej. "geonode:mexreg1"
        workspace = layer_name.split(":")[0]  # ej. "geonode"

        gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
        auth = (
            settings.OGC_SERVER["default"]["USER"],
            settings.OGC_SERVER["default"]["PASSWORD"],
        )

        # ----------------------------------------------------------------------
        # 1) Obtener estilos asociados a la capa
        # ----------------------------------------------------------------------
        url_styles = f"{gs_url}/rest/layers/{layer_name}/styles.json"
        r_styles = requests.get(url_styles, auth=auth)
        r_styles.raise_for_status()

        styles_data = r_styles.json()
        associated_styles = [s["name"] for s in styles_data.get("styles", {}).get("style", [])]

        # Obtener estilo por defecto
        url_layer = f"{gs_url}/rest/layers/{layer_name}.json"
        r_layer = requests.get(url_layer, auth=auth)
        r_layer.raise_for_status()

        default_style = (
            r_layer.json().get("layer", {}).get("defaultStyle", {}).get("name")
        )

        # ----------------------------------------------------------------------
        # 2) Normalizar el nombre del estilo
        # ----------------------------------------------------------------------
        is_download = False
        clean_name = style_name

        if style_name.endswith(".sld"):
            clean_name = style_name[:-4]
            is_download = True
        else:
            clean_name = style_name

        # Para efectos de comparación con GS, los estilos se listan así:
        # - "geonode:custommex"
        # - "custommex"
        # Así que normalizamos AMBOS formatos
        normalized_associated = set()
        for s in associated_styles + ([default_style] if default_style else []):
            if ":" in s:
                normalized_associated.add(s.split(":")[1])
            normalized_associated.add(s)

        # ----------------------------------------------------------------------
        # 3) Validar que el estilo esté asociado
        # ----------------------------------------------------------------------
        if clean_name not in normalized_associated and f"{workspace}:{clean_name}" not in normalized_associated:
            return Response(
                {"detail": f"Style '{clean_name}' is not associated with this dataset"},
                status=404,
            )

        # ----------------------------------------------------------------------
        # 4) Construir URLs posibles del estilo
        # ----------------------------------------------------------------------
        # A) URL EN WORKSPACE (ej. /rest/workspaces/geonode/styles/custommex.sld)
        ws_url = (
            f"{gs_url}/rest/workspaces/{workspace}/styles/{clean_name}.sld"
        )

        # B) URL GLOBAL (ej. /rest/styles/custommex.sld)
        global_url = f"{gs_url}/rest/styles/{clean_name}.sld"

        # ----------------------------------------------------------------------
        # 5) Intentar primero en workspace y luego global
        # ----------------------------------------------------------------------
        r = requests.get(ws_url, auth=auth)

        if r.status_code == 404:
            r = requests.get(global_url, auth=auth)

        if r.status_code == 404:
            raise NotFound(f"Style '{clean_name}' not found in GeoServer")

        r.raise_for_status()
        sld_content = r.text

        # ----------------------------------------------------------------------
        # 6) Responder
        # ----------------------------------------------------------------------
        if is_download:
            response = HttpResponse(sld_content, content_type="application/xml")
            response["Content-Disposition"] = f'attachment; filename="{clean_name}.sld"'
            return response

        return HttpResponse(sld_content, content_type="application/xml")

