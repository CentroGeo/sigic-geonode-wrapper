from geonode.layers.api.views import DatasetViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
from rest_framework.exceptions import NotFound
import requests
import json
from geonode.layers.utils import validate_sld
from rest_framework.exceptions import PermissionDenied


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

    @action(detail=True, methods=["post"], url_path="styles")
    def create_style(self, request, pk=None):
        """
        Crea un nuevo estilo SLD en GeoServer y lo asocia a la capa.
        - Valida permisos del usuario (GeoNode)
        - Acepta SLD como texto o archivo
        - Exclusividad (sólo uno permitido)
        - Valida el SLD con GeoNode
        - Crea estilo en workspace del dataset
        - Lo asocia a la capa
        """

        # -------------------------------------------------------------
        # 0) Permisos del dataset (GeoNode)
        # -------------------------------------------------------------
        dataset = self.get_object()
        self.check_object_permissions(request, dataset)  # 🔥 permisos reales de GeoNode

        layer_name = dataset.alternate                # ej. geonode:mexreg1
        workspace = layer_name.split(":")[0]          # ej. geonode

        gs = settings.OGC_SERVER["default"]
        gs_url = gs["LOCATION"].rstrip("/")
        auth = (gs["USER"], gs["PASSWORD"])

        # -------------------------------------------------------------
        # 1) Entrada: name + (sld ó sld_file)
        # -------------------------------------------------------------
        name = request.data.get("name")
        sld_text = request.data.get("sld")
        sld_file = request.FILES.get("sld_file")

        if not name:
            return Response({"detail": "`name` is required"}, status=400)

        # Exclusividad
        if sld_text and sld_file:
            return Response(
                {"detail": "Send either `sld` or `sld_file`, but not both"},
                status=400
            )

        if not sld_text and not sld_file:
            return Response(
                {"detail": "You must send either `sld` (text) or `sld_file` (file)"},
                status=400
            )

        # Archivo → convertir a texto
        if sld_file:
            try:
                sld_text = sld_file.read().decode("utf-8")
            except Exception:
                return Response(
                    {"detail": "SLD file could not be read as UTF-8 text"},
                    status=400
                )

        # No permitir nombres con ".sld"
        if name.lower().endswith(".sld"):
            return Response(
                {"detail": "Do not include .sld extension in the name"},
                status=400
            )

        # -------------------------------------------------------------
               # 2) Validación del SLD usando GeoNode (XML + XSD)
        # -------------------------------------------------------------
        is_valid, error_msg = validate_sld(sld_text)
        if not is_valid:
            return Response(
                {"detail": "Invalid SLD", "error": error_msg},
                status=400
            )

        # -------------------------------------------------------------
        # 3) Evitar estilos duplicados
        # -------------------------------------------------------------
        check_url = f"{gs_url}/rest/workspaces/{workspace}/styles/{name}.sld"
        check = requests.get(check_url, auth=auth)

        if check.status_code == 200:
            return Response(
                {"detail": f"Style '{name}' already exists"},
                status=409
            )

        # -------------------------------------------------------------
        # 4) Crear estilo en GeoServer (workspace)
        # -------------------------------------------------------------
        create_url = f"{gs_url}/rest/workspaces/{workspace}/styles?name={name}"

        headers_xml = {"Content-Type": "application/vnd.ogc.sld+xml"}

        r_create = requests.post(
            create_url,
            data=sld_text,
            auth=auth,
            headers=headers_xml
        )

        if r_create.status_code not in (200, 201):
            return Response(
                {
                    "detail": "GeoServer error creating style",
                    "geoserver_response": r_create.text
                },
                status=500
            )

        # -------------------------------------------------------------
        # 5) Asociar estilo a la capa
        # -------------------------------------------------------------
        assoc_url = f"{gs_url}/rest/layers/{layer_name}/styles"

        payload = {"style": {"name": f"{workspace}:{name}"}}

        r_assoc = requests.post(
            assoc_url,
            json=payload,
            auth=auth,
            headers={"Content-Type": "application/json"}
        )

        if r_assoc.status_code not in (200, 201):
            return Response(
                {
                    "detail": "Style created but not associated with layer",
                    "geoserver_response": r_assoc.text
                },
                status=500
            )

        # -------------------------------------------------------------
        # 6) Respuesta final
        # -------------------------------------------------------------
        return Response(
            {
                "status": "created",
                "style": name,
                "workspace": workspace,
                "layer": layer_name
            },
            status=201
        )
