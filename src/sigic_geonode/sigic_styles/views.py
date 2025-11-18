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
import xml.etree.ElementTree as ET
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
    OpenApiExample,
    OpenApiParameter,
    inline_serializer,
)
from rest_framework import serializers

ListStylesResponse = inline_serializer(
    name="ListSLDStylesResponse",
    fields={
        "layer": serializers.CharField(),
        "default_style": serializers.CharField(allow_null=True),
        "styles": serializers.ListField(child=serializers.CharField()),
    }
)

SetDefaultRequest = inline_serializer(
    name="SetDefaultSLDRequest",
    fields={"style": serializers.CharField()}
)

CreateUpdateStyleRequest = inline_serializer(
    name="CreateOrUpdateSLDStyleRequest",
    fields={
        "name": serializers.CharField(required=False),
        "sld_file": serializers.FileField(required=False),
        "sld_body": serializers.CharField(required=False),
    }
)


@extend_schema_view(
    list=extend_schema(
        summary="Lista estilos asociados al dataset",
        responses={200: ListStylesResponse},
        tags=["SLD Styles"],
    ),

    retrieve=extend_schema(
        summary="Obtiene el SLD de un estilo asociado",
        parameters=[
            OpenApiParameter(
                name="download",
                description="Si es 'true', descarga el estilo como .sld",
                required=False,
                type=bool,
            )
        ],
        responses={
            200: OpenApiResponse(
                description="SLD obtenido correctamente",
            ),
            404: OpenApiResponse(description="Estilo no encontrado"),
        },
        tags=["SLD Styles"],
    ),

    create=extend_schema(
        summary="Crea un nuevo estilo y lo asocia al dataset",
        request=CreateUpdateStyleRequest,
        responses={
            201: OpenApiResponse(description="Estilo creado correctamente"),
            400: OpenApiResponse(description="Error en parámetros enviados"),
            409: OpenApiResponse(description="El estilo ya existe"),
        },
        tags=["SLD Styles"],
    ),

    update=extend_schema(
        summary="Actualiza el contenido (SLD) de un estilo existente",
        request=CreateUpdateStyleRequest,
        responses={
            200: OpenApiResponse(description="Estilo actualizado correctamente"),
            404: OpenApiResponse(description="Estilo no existe"),
        },
        tags=["SLD Styles"],
    ),

    destroy=extend_schema(
        summary="Elimina un estilo asociado al dataset",
        responses={
            200: OpenApiResponse(description="Estilo eliminado correctamente"),
            400: OpenApiResponse(description="Intento de eliminar estilo por defecto"),
            404: OpenApiResponse(description="Estilo no encontrado"),
        },
        tags=["SLD Styles"],
    ),
)
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

    # GET /api/v2/datasets/<id>/sldstyles/<style_name>/
    def retrieve(self, request, dataset_pk=None, pk=None):
        """
        Devuelve el SLD de un estilo asociado al dataset.
        - Si pk termina en '.sld', lo descarga como archivo.
        - Valida que el estilo esté realmente asociado.
        - Soporta nombres extendidos 'workspace:style' y locales 'style'.
        """
        dataset = self._get_dataset_or_404(dataset_pk)
        layer_name = dataset.alternate  # ej: geonode:immziszen_colonias
        workspace = layer_name.split(":")[0]  # ej: geonode

        gs = settings.OGC_SERVER["default"]
        gs_url = gs["LOCATION"].rstrip("/")
        auth = (gs["USER"], gs["PASSWORD"])

        # -------------------------------------------
        # 1. Normalizar nombre solicitado
        # -------------------------------------------
        requested = pk  # pk viene de la URL
        is_download = request.query_params.get("download") in ("1", "true", "yes") or requested.endswith(".sld")
        clean_name = requested[:-4] if is_download else requested  # "acatic3"

        # -------------------------------------------
        # 2. Obtener estilos asociados del layer
        # -------------------------------------------
        r_styles = requests.get(
            f"{gs_url}/rest/layers/{layer_name}/styles.json",
            auth=auth
        )
        if r_styles.status_code != 200:
            return Response({"detail": "Error consultando estilos en GeoServer"}, status=500)

        styles = r_styles.json().get("styles", {}).get("style", [])
        associated = set()

        for s in styles:
            name = s.get("name")  # ej: "geonode:acatic3"
            if not name:
                continue
            associated.add(name)  # forma extendida
            if ":" in name:
                associated.add(name.split(":", 1)[1])  # forma local "acatic3"

        # También incluir defaultStyle
        r_layer = requests.get(
            f"{gs_url}/rest/layers/{layer_name}.json",
            auth=auth
        )
        if r_layer.status_code == 200:
            default_name = (
                r_layer.json()
                .get("layer", {})
                .get("defaultStyle", {})
                .get("name")
            )
            if default_name:
                associated.add(default_name)
                if ":" in default_name:
                    associated.add(default_name.split(":", 1)[1])

        # -------------------------------------------
        # 3. Validar que el estilo esté asociado
        # -------------------------------------------
        if clean_name not in associated:
            return Response(
                {"detail": f"El estilo '{clean_name}' no está asociado a este dataset"},
                status=404
            )

        # -------------------------------------------
        # 4. Intentar obtener el SLD desde workspace (primero)
        # -------------------------------------------
        ws_url = f"{gs_url}/rest/workspaces/{workspace}/styles/{clean_name}.sld"
        global_url = f"{gs_url}/rest/styles/{clean_name}.sld"

        r = requests.get(ws_url, auth=auth)
        if r.status_code == 404:
            r = requests.get(global_url, auth=auth)

        if r.status_code == 404:
            return Response({"detail": f"El estilo '{clean_name}' no existe en GeoServer"}, status=404)

        if r.status_code != 200:
            return Response({"detail": "Error obteniendo SLD de GeoServer"}, status=500)

        sld = r.text

        # -------------------------------------------
        # 5. Si pidió descarga (*.sld)
        # -------------------------------------------
        if is_download:
            resp = HttpResponse(sld, content_type="application/xml")
            resp["Content-Disposition"] = f'attachment; filename="{clean_name}.sld"'
            return resp

        # -------------------------------------------
        # 6. Visualización normal del SLD
        # -------------------------------------------
        return HttpResponse(sld, content_type="application/xml")

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

    # PUT /api/v2/datasets/<id>/sldstyles/<style_name>/
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

    # DELETE /api/v2/datasets/<id>/sldstyles/<style_name>/
    def destroy(self, request, dataset_pk=None, pk=None):
        # pk es el nombre del estilo en la URL
        name = pk

        dataset = self._get_dataset_or_404(dataset_pk)
        layer_name = dataset.alternate  # ej: geonode:immziszen_colonias
        workspace = layer_name.split(":")[0]  # ej: geonode

        self._check_edit_perm(dataset, request.user)

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

    # POST /api/v2/datasets/<id>/sldstyles/set-default/
    @extend_schema(
        summary="Cambia el estilo por defecto del dataset",
        request=SetDefaultRequest,
        responses={
            200: OpenApiResponse(
                description="Estilo por defecto actualizado correctamente",
                response=inline_serializer(
                    name="SetDefaultResponse",
                    fields={
                        "message": serializers.CharField(),
                        "default": serializers.CharField(),
                    }
                )
            ),
            400: OpenApiResponse(description="El estilo no está asociado"),
        },
        tags=["SLD Styles"],
    )
    @action(detail=False, methods=["post"], url_path="set-default")
    def set_default_style(self, request, dataset_pk=None):
        """
        Cambia el estilo por defecto del layer.
        Endpoint: POST /datasets/<id>/sldstyles/set-default/
        Body: { "style": "custommex" }
        """
        style_name = request.data.get("style")
        if not style_name:
            return Response({"error": "Debe incluir 'style' en el body."}, status=400)

        dataset = self._get_dataset_or_404(dataset_pk)
        layer_name = dataset.alternate
        workspace = layer_name.split(":")[0]

        self._check_edit_perm(dataset, request.user)

        gs = settings.OGC_SERVER["default"]
        gs_url = gs["LOCATION"].rstrip("/")
        auth = (gs["USER"], gs["PASSWORD"])

        # nombre extendido
        new_default_full = f"{workspace}:{style_name}"

        # 1) Obtener XML completo del layer
        url_layer = f"{gs_url}/rest/layers/{layer_name}.xml"

        r_get = requests.get(url_layer, auth=auth)
        if r_get.status_code != 200:
            return Response({"error": "GeoServer no devolvió el layer"}, status=500)

        tree = ET.fromstring(r_get.text)

        # default actual
        current_default = tree.find("./defaultStyle/name")
        current_default_name = current_default.text if current_default is not None else None

        # styles asociados
        styles_node = tree.find("./styles")
        associated = set()

        for s in styles_node.findall("style"):
            nm = s.find("name")
            if nm is not None:
                associated.add(nm.text)

        # incluir también default actual
        if current_default_name:
            associated.add(current_default_name)

        # validar que el estilo exista
        if new_default_full not in associated:
            return Response(
                {"error": f"El estilo '{style_name}' no está asociado al dataset."},
                status=400,
            )

        # 2) mover default actual a <styles> si no está
        if current_default_name and current_default_name != new_default_full:
            found = False
            for s in styles_node.findall("style"):
                nm = s.find("name")
                if nm is not None and nm.text == current_default_name:
                    found = True
                    break
            if not found:
                st = ET.Element("style")
                nm = ET.SubElement(st, "name")
                nm.text = current_default_name
                ws_el = ET.SubElement(st, "workspace")
                ws_el.text = workspace
                styles_node.append(st)

        # 3) quitar nuevo default de <styles> si está ahí
        for s in list(styles_node.findall("style")):
            nm = s.find("name")
            if nm is not None and nm.text == new_default_full:
                styles_node.remove(s)
                break

        # 4) actualizar defaultStyle
        default_style_node = tree.find("./defaultStyle")
        if default_style_node is None:
            default_style_node = ET.SubElement(tree, "defaultStyle")

        # limpiar contenido
        for ch in list(default_style_node):
            default_style_node.remove(ch)

        nm = ET.SubElement(default_style_node, "name")
        nm.text = new_default_full
        ws_el = ET.SubElement(default_style_node, "workspace")
        ws_el.text = workspace

        # 5) PUT del XML actualizado
        updated_xml = ET.tostring(tree, encoding="utf-8")
        r_put = requests.put(
            url_layer,
            data=updated_xml,
            auth=auth,
            headers={"Content-Type": "application/xml"},
        )

        if r_put.status_code not in (200, 201):
            return Response({"error": "GeoServer rechazó el update"}, status=500)

        return Response(
            {
                "message": "Estilo por defecto actualizado correctamente",
                "default": style_name,
            }
        )
