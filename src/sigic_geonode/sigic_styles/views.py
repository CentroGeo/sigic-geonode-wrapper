import os
from geonode.layers.api.views import DatasetViewSet
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
from rest_framework.exceptions import NotFound
import requests
import json
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import PermissionDenied, NotFound
from geonode.layers.models import Dataset
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import status as drf_status


class SigicDatasetViewSet(DatasetViewSet):

    def _list_styles(self, request, pk=None):
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

    def _create_style(self, request, pk=None):
        dataset = self.get_object()
        self.check_object_permissions(request, dataset)

        layer_name = dataset.alternate
        workspace = layer_name.split(":")[0]

        gs = settings.OGC_SERVER["default"]
        gs_url = gs["LOCATION"].rstrip("/")
        auth = (gs["USER"], gs["PASSWORD"])

        # -----------------------------
        # 1) Entrada
        # -----------------------------
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

        # Archivo → texto
        if sld_file:
            try:
                sld_text = sld_file.read().decode("utf-8")
            except Exception:
                return Response(
                    {"detail": "SLD file could not be read as UTF-8 text"},
                    status=400
                )

        if name.lower().endswith(".sld"):
            return Response(
                {"detail": "Do not include .sld extension"}, status=400
            )

        # -----------------------------
        # 2) Validar SLD usando GeoServer
        # -----------------------------
        is_valid, error_msg = self._validate_sld_with_geoserver(sld_text, gs_url, auth)
        if not is_valid:
            return Response(
                {"detail": "Invalid SLD", "error": error_msg},
                status=400
            )

        # -----------------------------
        # 3) Verificar existencia previa
        # -----------------------------
        check_url = f"{gs_url}/rest/workspaces/{workspace}/styles/{name}.sld"
        r_check = requests.get(check_url, auth=auth)
        if r_check.status_code == 200:
            return Response(
                {"detail": f"Style '{name}' already exists"},
                status=409
            )

        # -----------------------------
        # 4) Crear estilo en GeoServer
        # -----------------------------
        create_url = f"{gs_url}/rest/workspaces/{workspace}/styles?name={name}&raw=true"
        headers_xml = {"Content-Type": "application/vnd.ogc.sld+xml"}

        r_create = requests.post(
            create_url, data=sld_text, auth=auth, headers=headers_xml
        )

        if r_create.status_code not in (200, 201):
            return Response(
                {"detail": "GeoServer error creating style",
                 "geoserver_response": r_create.text},
                status=500
            )

        # -----------------------------
        # 5) Asociar estilo a la capa
        # -----------------------------
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
                {"detail": "Style created but not associated with layer",
                 "geoserver_response": r_assoc.text},
                status=500
            )

        # -----------------------------
        # 6) Respuesta OK
        # -----------------------------
        return Response(
            {
                "status": "created",
                "style": name,
                "workspace": workspace,
                "layer": layer_name
            },
            status=201
        )

    def _validate_sld_with_geoserver(self, sld_text, gs_url, auth):
        """
        Valida un SLD usando GeoServer:
        POST /rest/styles?validate=true
        """
        validate_url = f"{gs_url}/rest/styles?validate=true"

        headers = {"Content-Type": "application/vnd.ogc.sld+xml"}

        r = requests.post(validate_url, data=sld_text, headers=headers, auth=auth)

        if r.status_code in (200, 201):
            return True, None

        error_msg = r.text.strip() or "GeoServer validation failed"
        return False, error_msg

    @action(detail=True, methods=["get"], url_path="ping")
    def ping(self, request, pk=None):
        return Response({"status": "ok"})

    @action(detail=True, methods=["get", "post"], url_path="sldstyles")
    def sldstyles(self, request, pk=None):
        print("Request method:", request.method)
        if request.method == "GET":
            return self._list_styles(request, pk)
        elif request.method == "POST":
            return self._create_style(request, pk)
        else:
            return Response({"detail": "Method not allowed"}, status=405)

    @action(detail=True, methods=["get"], url_path=r"sldstyles/(?P<style_name>[^/]+)$")
    def get_sldstyle(self, request, pk=None, style_name=None):
        print(">>> ENTRO A get_style() CON", request.method, "style_name=", style_name)
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


class SigicDatasetSLDStyleViewSet(ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    # -----------------------------
    # Helpers de permisos
    # -----------------------------
    def _get_dataset_or_404(self, dataset_pk):
        try:
            return Dataset.objects.get(pk=dataset_pk)
        except Dataset.DoesNotExist:
            raise NotFound("Dataset not found")

    def _check_view_perm(self, dataset, user):
        """
        Permite ver el dataset si:
        - Es público, o
        - El usuario tiene permiso view_resourcebase en el ResourceBase asociado
        """

        # Caso 1: acceso público
        if dataset.is_published and dataset.is_approved:
            return

        # Caso 2: usuario autenticado con permiso de lectura
        if user and user.is_authenticated:
            if user.has_perm("base.view_resourcebase", dataset.resourcebase_ptr):
                return

        raise PermissionDenied("You do not have permission to view this dataset.")

    def _check_edit_perm(self, dataset, user):
        """
        Permite modificar estilos si:
        - Usuario autenticado con permiso change_layer_style
        - o superuser
        """
        if not (user and user.is_authenticated):
            raise PermissionDenied("Authentication required.")

        # superuser → acceso total
        if user.is_superuser:
            return

        if user.has_perm("base.change_layer_style", dataset.resourcebase_ptr):
            return

        raise PermissionDenied("You do not have permission to modify styles.")

    # GET /api/v2/datasets/<id>/sldstyles/
    def list(self, request, dataset_pk=None):
        dataset = self._get_dataset_or_404(dataset_pk)
        self._check_view_perm(dataset, request.user)

        layer_name = dataset.alternate

        gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
        auth = (
            settings.OGC_SERVER["default"]["USER"],
            settings.OGC_SERVER["default"]["PASSWORD"],
        )

        # --- 1. Estilos asociados (lista completa de estilos configurados en la capa) ---
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

        default_style = (
            layer_data.get("layer", {})
            .get("defaultStyle", {})
            .get("name")
        )

        # Normalizar workspace:name → name
        if default_style and ":" in default_style:
            default_style = default_style.split(":")[-1]

        return Response({
            "layer": layer_name,
            "default_style": default_style,
            "styles": associated_styles,
        })

    # GET /api/v2/datasets/<id>/sldstyles/<style_name>
    def retrieve(self, request, dataset_pk=None, pk=None):
        dataset = self._get_dataset_or_404(dataset_pk)
        self._check_view_perm(dataset, request.user)
        return Response({"status": "ok", "scope": "retrieve", "style": pk})

    # POST /api/v2/datasets/<id>/sldstyles/
    def create(self, request, dataset_pk=None):
        dataset = self._get_dataset_or_404(dataset_pk)
        layer_name = dataset.alternate
        workspace = layer_name.split(":")[0]
        self._check_edit_perm(dataset, request.user)

        name = request.data.get("name")
        sld_file = request.FILES.get("sld_file")
        sld_body = request.data.get("sld_body")

        # ---------------------------------------------
        # Validación: solo uno de los dos
        # ---------------------------------------------
        if sld_file and sld_body:
            return Response(
                {"error": "Debes enviar *solo uno* de: 'sld_file' o 'sld_body'."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        if not sld_file and not sld_body:
            return Response(
                {"error": "Debes enviar 'sld_file' (SLD) o 'sld_body' (cuerpo XML)."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        if not name:
            return Response(
                {"error": "Falta el parámetro obligatorio 'name'."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
        auth = (
            settings.OGC_SERVER["default"]["USER"],
            settings.OGC_SERVER["default"]["PASSWORD"],
        )

        # ---------------------------------------------
        # 1) Crear entrada del estilo (POST)
        # ---------------------------------------------
        url_create = f"{gs_url}/rest/workspaces/{workspace}/styles"

        wrapper = f"""
        <style>
            <name>{name}</name>
            <filename>{name}.sld</filename>
        </style>
        """

        r_post = requests.post(
            url_create,
            data=wrapper,
            auth=auth,
            headers={"Content-Type": "text/xml"},
        )

        if r_post.status_code not in (200, 201):
            return Response(
                {
                    "error": "GeoServer rechazó la creación del estilo",
                    "gs_status": r_post.status_code,
                    "gs_response": r_post.text,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        # ---------------------------------------------
        # 2) Subir SLD (PUT)
        # ---------------------------------------------
        if sld_file:
            sld_body = sld_file.read()
        else:
            sld_body = sld_body.encode("utf-8")

        url_upload = f"{gs_url}/rest/workspaces/{workspace}/styles/{name}"

        r_put = requests.put(
            url_upload,
            data=sld_body,
            auth=auth,
            headers={"Content-Type": "application/vnd.ogc.sld+xml"},
        )

        if r_put.status_code not in (200, 201):
            return Response(
                {
                    "error": "GeoServer rechazó el SLD",
                    "gs_status": r_put.status_code,
                    "gs_response": r_put.text,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        # ---------------------------------------------
        # 3) Asociar estilo a la capa (POST)
        # ---------------------------------------------
        url_layer_styles = f"{gs_url}/rest/layers/{layer_name}/styles"

        xml_body = f"<style><name>{name}</name></style>"

        r_post_layer = requests.post(
            url_layer_styles,
            data=xml_body,
            auth=auth,
            headers={"Content-Type": "application/xml"},
        )

        if r_post_layer.status_code not in (200, 201):
            return Response(
                {
                    "error": "No se pudo asociar el estilo a la capa",
                    "gs_status": r_post_layer.status_code,
                    "gs_response": r_post_layer.text,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        # ---------------------------------------------
        # Final exitoso
        # ---------------------------------------------
        return Response(
            {
                "message": "Estilo creado y asociado correctamente",
                "style": name,
                "layer": layer_name,
            },
            status=drf_status.HTTP_201_CREATED,
        )

    # PUT /api/v2/datasets/<id>/sldstyles/<style_name>
    def update(self, request, dataset_pk=None, pk=None):
        """
        Actualiza el contenido de un estilo SLD existente en GeoServer.
        `pk` es el nombre del estilo.
        """
        dataset = self._get_dataset_or_404(dataset_pk)
        layer_name = dataset.alternate
        workspace = layer_name.split(":")[0]

        self._check_edit_perm(dataset, request.user)

        name = pk  # nombre del estilo
        sld_file = request.FILES.get("sld_file")
        sld_body = request.data.get("sld_body")

        # ---------------------------------------------
        # Validación: solo uno de los dos
        # ---------------------------------------------
        if sld_file and sld_body:
            return Response(
                {"error": "Debes enviar *solo uno* de: 'sld_file' o 'sld_body'."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        if not sld_file and not sld_body:
            return Response(
                {"error": "Debes enviar 'sld_file' (SLD) o 'sld_body' (cuerpo XML)."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------
        # Seleccionar cuerpo SLD
        # ---------------------------------------------
        if sld_file:
            sld_body = sld_file.read()
        else:
            sld_body = sld_body.encode("utf-8")

        gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
        auth = (
            settings.OGC_SERVER["default"]["USER"],
            settings.OGC_SERVER["default"]["PASSWORD"],
        )

        # ---------------------------------------------
        # 1. Verificar que el estilo exista (opcional pero útil)
        # ---------------------------------------------
        url_check = f"{gs_url}/rest/workspaces/{workspace}/styles/{name}.xml"
        r_check = requests.get(url_check, auth=auth)

        if r_check.status_code != 200:
            return Response(
                {
                    "error": "El estilo no existe en GeoServer",
                    "style": name,
                    "gs_status": r_check.status_code,
                    "gs_response": r_check.text,
                },
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------------------------
        # 2. Actualizar el SLD (PUT) — DOCUMENTACIÓN OFICIAL
        # ---------------------------------------------
        url_update = f"{gs_url}/rest/workspaces/{workspace}/styles/{name}"

        r_put = requests.put(
            url_update,
            data=sld_body,
            auth=auth,
            headers={"Content-Type": "application/vnd.ogc.sld+xml"},
        )

        if r_put.status_code not in (200, 201):
            return Response(
                {
                    "error": "GeoServer rechazó la actualización del SLD",
                    "gs_status": r_put.status_code,
                    "gs_response": r_put.text,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        # ---------------------------------------------
        # Final exitoso
        # ---------------------------------------------
        return Response(
            {
                "message": "Estilo actualizado correctamente",
                "style": name,
                "layer": layer_name,
            },
            status=drf_status.HTTP_200_OK,
        )

    # DELETE /api/v2/datasets/<id>/sldstyles/<style_name>
    def destroy(self, request, dataset_pk=None, pk=None):
        # pk es el nombre del estilo en la URL
        name = pk

        dataset = self._get_dataset_or_404(dataset_pk)
        layer_name = dataset.alternate  # ej: geonode:immziszen_colonias
        workspace = layer_name.split(":")[0]  # ej: geonode

        # Nombre REAL del estilo en GeoServer
        full_style_name = f"{workspace}:{name}"

        gs_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
        auth = (
            settings.OGC_SERVER["default"]["USER"],
            settings.OGC_SERVER["default"]["PASSWORD"],
        )

        # 1. GET del layer
        url_layer = f"{gs_url}/rest/layers/{layer_name}.xml"
        r_get = requests.get(url_layer, auth=auth)

        if r_get.status_code != 200:
            return Response(
                {"error": "No se pudo obtener el layer para actualizar estilos",
                 "gs_status": r_get.status_code,
                 "gs_response": r_get.text},
                status=drf_status.HTTP_502_BAD_GATEWAY
            )

        import xml.etree.ElementTree as ET
        tree = ET.fromstring(r_get.text)

        # 2. Validar default
        default_style = tree.find("./defaultStyle/name")
        if default_style is not None and default_style.text == full_style_name:
            return Response(
                {"error": "No se puede eliminar un estilo que es el estilo por defecto."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        # 3. Extraer estilos existentes
        styles_node = tree.find("./styles")
        if styles_node is None:
            return Response(
                {"error": "El nodo <styles> no existe en el layer."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        # 4. Quitar el estilo (extended mode)
        removed = False
        for style in list(styles_node.findall("style")):
            name_node = style.find("name")
            if name_node is not None and name_node.text == full_style_name:
                styles_node.remove(style)
                removed = True
                break

        if not removed:
            return Response(
                {"error": f"El estilo '{full_style_name}' no está asociado a la capa."},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        # 5. PUT del layer actualizado
        final_xml = ET.tostring(tree, encoding="utf-8")
        r_put = requests.put(
            url_layer,
            data=final_xml,
            auth=auth,
            headers={"Content-Type": "application/xml"}
        )

        if r_put.status_code not in (200, 201):
            return Response(
                {
                    "error": "No se pudo actualizar la lista de estilos en el layer",
                    "gs_status": r_put.status_code,
                    "gs_response": r_put.text,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        # 6. DELETE del estilo del workspace usando su nombre completo
        url_delete_style = (
            f"{gs_url}/rest/workspaces/{workspace}/styles/{name}?purge=true"
        )

        r_del = requests.delete(url_delete_style, auth=auth)

        if r_del.status_code not in (200, 201):
            return Response(
                {
                    "error": "GeoServer no pudo eliminar el estilo",
                    "style": full_style_name,
                    "gs_status": r_del.status_code,
                    "gs_response": r_del.text,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message": "Estilo eliminado correctamente",
                "style": full_style_name,
            },
            status=drf_status.HTTP_200_OK,
        )
