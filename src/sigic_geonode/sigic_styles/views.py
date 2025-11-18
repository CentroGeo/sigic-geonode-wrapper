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
    """
    API especializada para gestionar estilos SLD (Styled Layer Descriptor)
    de un dataset dentro de GeoServer.

    Este ViewSet permite:
    - Listar estilos asociados a una capa (GeoServer REST)
    - Descargar o visualizar un estilo SLD específico
    - Crear nuevos estilos y asociarlos al layer
    - Actualizar el contenido XML de un estilo existente
    - Eliminar estilos asociados (con purga automática)
    - Cambiar el estilo por defecto del layer

    Toda la gestión se realiza contra el endpoint REST nativo de GeoServer,
    manipulando tanto la configuración del estilo como la del layer
    (modo extendido), asegurando consistencia y seguridad.

    NOTA:
    - Los permisos se basan en los permisos propios de GeoNode.
    - Se respeta el comportamiento de `defaultStyle`: no puede eliminarse.
    - Los estilos siempre se interpretan dentro del workspace derivado
      del dataset (p.ej. “geonode”).
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    # -----------------------------
    # Helpers de permisos
    # -----------------------------
    def _get_dataset_or_404(self, dataset_pk):
        """
        Obtiene el objeto Dataset correspondiente al `dataset_pk`.
        Si no existe, lanza una excepción `NotFound` estándar de DRF.

        Parámetros
        ----------
        dataset_pk : int or str
            ID del dataset recibido desde la URL del ViewSet.

        Retorna
        -------
        Dataset
            El dataset solicitado si existe.

        Excepciones
        -----------
        NotFound
            Si el dataset no existe en la base de datos.

        Notas
        -----
        Este método se utiliza como helper interno en todos los endpoints
        del ViewSet que requieren validar la existencia del dataset antes
        de cualquier operación.
        """
        try:
            return Dataset.objects.get(pk=dataset_pk)
        except Dataset.DoesNotExist:
            raise NotFound("Dataset not found")

    def _check_view_perm(self, dataset, user):
        """
        Verifica si un usuario tiene permiso para *ver* el dataset.

        Reglas aplicadas
        ----------------
        1. Si el dataset está publicado **y** aprobado (`is_published` + `is_approved`),
           el acceso es público y se permite a cualquier usuario, autenticado o no.

        2. Si el usuario está autenticado, se le permite el acceso únicamente si
           posee el permiso `base.view_resourcebase` sobre el `resourcebase_ptr`
           del dataset.

        3. Si ninguna condición se cumple, se lanza `PermissionDenied`.

        Parámetros
        ----------
        dataset : Dataset
            El dataset cuyo acceso se está validando.

        user : User
            Usuario que realiza la solicitud.

        Excepciones
        -----------
        PermissionDenied
            Cuando el usuario no tiene permiso para acceder al recurso.

        Notas
        -----
        Este método centraliza la lógica de lectura, alineándola con la forma en que
        GeoNode maneja la visibilidad de los recursos.
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
        Verifica si un usuario tiene permisos para modificar estilos del dataset.

        Reglas aplicadas
        ----------------
        1. El usuario debe estar autenticado.
           Si no lo está, se lanza inmediatamente `PermissionDenied`.

        2. Si el usuario es `superuser`, se permite la edición sin más validaciones.

        3. Para usuarios normales, solo se permite continuar si tienen el permiso
           `base.change_layer_style` sobre el `resourcebase_ptr` del dataset.

        Si ninguna condición se cumple, se lanza `PermissionDenied`.

        Parámetros
        ----------
        dataset : Dataset
            El dataset cuyo permiso de edición se está evaluando.

        user : User
            Usuario autenticado que realiza la solicitud.

        Excepciones
        -----------
        PermissionDenied
            Cuando el usuario no posee los permisos requeridos.

        Notas
        -----
        - Este método define *quién puede modificar estilos SLD*, de forma coherente
          con los permisos de GeoNode.
        - Se usa en `create`, `update` y `destroy` de estilos SLD.
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
        """
        Lista todos los estilos SLD asociados al dataset, incluyendo el estilo por
        defecto y los estilos adicionales configurados en GeoServer.

        Descripción
        -----------
        Este endpoint consulta GeoServer usando la API REST y devuelve:

        - El nombre completo del layer (workspace:name)
        - El estilo por defecto del layer (en forma simple: "estilo")
        - La lista de estilos asociados al layer (formato "estilo" sin workspace)

        Flujo interno
        -------------
        1. Verifica permisos de lectura mediante `_check_view_perm`.
        2. Obtiene desde GeoServer:
           - `/rest/layers/<layer>/styles.json`
             → estilos adicionales asociados
           - `/rest/layers/<layer>.json`
             → estilo por defecto
        3. Normaliza los nombres removiendo el prefijo `<workspace>:` cuando existe.
        4. Retorna los datos en formato JSON.

        Parámetros
        ----------
        request : Request
            La solicitud HTTP recibida.

        dataset_pk : int
            ID del dataset cuyos estilos serán listados.

        Respuesta
        ---------
        HTTP 200
            Un diccionario con:
            - ``layer`` : nombre del layer
            - ``default_style`` : estilo por defecto
            - ``styles`` : lista de estilos asociados (no incluye el default)

        Excepciones
        -----------
        PermissionDenied
            Si el usuario no tiene permiso para ver el dataset.

        NotFound
            Si el dataset no existe.

        Notas
        -----
        - Este método **no** devuelve el contenido de los estilos, solo los nombres.
        - El contenido del SLD se obtiene mediante `retrieve()`.
        """

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
        Obtiene el contenido SLD de un estilo asociado al dataset.

        Este método sirve tanto para:
          - **Visualizar** el SLD directamente (XML en la respuesta)
          - **Descargar** el SLD como archivo `.sld` (si `?download=true` o si el nombre termina en `.sld` (esta última forma aun funciona correctamente))

        Descripción detallada
        ---------------------
        1. Valida que el dataset exista.
        2. Construye el nombre simple del estilo removiendo la extensión `.sld` en caso de descarga.
        3. Consulta GeoServer para obtener la lista real de estilos asociados al layer:
             - `/rest/layers/<layer>/styles.json`
             - Incluye estilos adicionales y también el `defaultStyle`.
        4. Verifica que el estilo solicitado esté realmente asociado al dataset.
        5. Intenta obtener el SLD desde:
             a. `/rest/workspaces/<workspace>/styles/<name>.sld`
             b. `/rest/styles/<name>.sld` (fallback)
        6. Retorna:
             - XML directo (visualización)
             - O bien un archivo descargable (`Content-Disposition: attachment`) si se pidió descarga.

        Parámetros
        ----------
        request : Request
            La solicitud HTTP, usada también para leer el query param `download`.

        dataset_pk : int
            ID del dataset desde el cual se obtiene el estilo.

        pk : str
            Nombre del estilo solicitado. Puede venir como:
            - `nombre`
            - `nombre.sld` (modo descarga)

        Respuestas
        ----------
        HTTP 200
            - XML con el SLD (visualización)
            - Archivo `.sld` si se solicitó descarga

        HTTP 404
            Si el estilo existe en GeoServer pero **no está asociado al dataset**.

        HTTP 500
            Si ocurre algún error inesperado al consultar GeoServer.

        Ejemplos
        --------
        Obtener estilo:
            GET /api/v2/datasets/12/sldstyles/estilo1/

        Descargar estilo:
            GET /api/v2/datasets/12/sldstyles/estilo1.sld

            GET /api/v2/datasets/12/sldstyles/estilo1/?download=true

        Notas
        -----
        - El método reconoce formas extendidas (`workspace:style`) y locales (`style`).
        - Esta es la única operación que devuelve contenido SLD directamente.
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
        """
        Crea un nuevo estilo SLD en GeoServer y lo asocia al dataset.

        Funcionalidad
        -------------
        Este endpoint permite subir un nuevo estilo SLD ya sea como:
          - `sld_file` (archivo real)
          - `sld_body` (cadena XML enviada en el body)

        El nombre del estilo (`name`) es obligatorio.

        Flujo interno
        -------------
        1. Verifica que el usuario tenga permisos de edición (`_check_edit_perm`).
        2. Valida que se haya enviado **solo uno** de:
             - `sld_file`
             - `sld_body`
        3. Crea la entrada del estilo en GeoServer mediante:
             POST /rest/workspaces/<workspace>/styles
        4. Sube el contenido SLD con:
             PUT /rest/workspaces/<workspace>/styles/<name>
        5. Asocia el estilo a la capa:
             POST /rest/layers/<layer>/styles
        6. Retorna un 201 si todo fue exitoso.

        Parámetros
        ----------
        request : Request
            Contiene:
            - `name`: nombre del estilo (string, requerido)
            - `sld_file`: archivo SLD (opcional)
            - `sld_body`: contenido XML del SLD (opcional)

        dataset_pk : int
            ID del dataset cuyo layer recibirá el estilo.

        Respuestas
        ----------
        HTTP 201
            El estilo fue creado y asociado correctamente.

        HTTP 400
            - Falta `name`
            - No se envió `sld_file` ni `sld_body`
            - Se enviaron ambos al mismo tiempo (exclusión obligatoria)

        HTTP 502
            Si GeoServer rechaza la creación o asociación del estilo.

        Notas
        -----
        - Este método no valida el contenido del SLD más allá de lo que GeoServer responde.
        - Los estilos se crean siempre dentro del workspace del dataset.
        - El nombre no debe llevar extensión `.sld`.
        """

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
        Actualiza el contenido SLD de un estilo existente en GeoServer.

        Funcionalidad
        -------------
        Este método reemplaza completamente el contenido del SLD asociado a un estilo.
        Permite enviar el nuevo contenido de dos formas exclusivas:

        - `sld_file`: archivo SLD real
        - `sld_body`: contenido XML en texto plano

        El nombre del estilo a actualizar se obtiene del parámetro `pk`.

        Flujo interno
        -------------
        1. Verifica que el usuario tenga permisos para modificar estilos
           mediante `_check_edit_perm`.

        2. Asegura que se envíe **solo uno** de:
             - `sld_file`
             - `sld_body`

        3. Comprueba que el estilo exista en GeoServer:
             GET /rest/workspaces/<workspace>/styles/<name>.xml

        4. Si existe, sube el nuevo contenido del SLD con:
             PUT /rest/workspaces/<workspace>/styles/<name>

        5. Responde con éxito o con el error devuelto por GeoServer.

        Parámetros
        ----------
        request : Request
            Contiene uno de:
            - `sld_file` : archivo SLD
            - `sld_body` : string XML

        dataset_pk : int
            ID del dataset al que pertenece el estilo.

        pk : str
            Nombre del estilo a actualizar (sin `.sld`).

        Respuestas
        ----------
        HTTP 200
            Estilo actualizado correctamente.

        HTTP 400
            - No se envió ningún contenido
            - Se enviaron ambos (`sld_file` y `sld_body`)

        HTTP 404
            El estilo no existe en GeoServer.

        HTTP 502
            GeoServer rechazó el PUT del SLD.

        Notas
        -----
        - No modifica la lista de estilos asociados ni el estilo por defecto.
        - Solo reemplaza el archivo SLD.
        - Debe usarse únicamente sobre estilos que ya existen.
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
        """
        Elimina un estilo SLD del dataset y de GeoServer de forma segura.

        Este método realiza dos operaciones:
        1. **Quita el estilo de la lista de estilos asociados al layer**
           (modificando el `<styles>` del layer en modo extendido).
        2. **Elimina el estilo en GeoServer** usando `purge=true`
           para borrar también el archivo `.sld`.

        Reglas importantes
        ------------------
        - **No permite eliminar el estilo por defecto del layer.**
          Si el estilo solicitado es el default, la operación se cancela con error 400.

        Flujo interno
        -------------
        1. Verifica que el usuario tenga permisos mediante `_check_edit_perm`.
        2. Obtiene el XML del layer:
             GET /rest/layers/<layer>.xml
        3. Determina si el estilo solicitado:
             - Está asociado
             - Es estilo por defecto
        4. Si está asociado y no es default:
             - Se remueve del nodo `<styles>`
             - PUT del layer actualizado
        5. Finalmente elimina el estilo:
             DELETE /rest/workspaces/<workspace>/styles/<name>?purge=true

        Parámetros
        ----------
        request : Request
            Solicitud HTTP.

        dataset_pk : int
            ID del dataset cuyo estilo se desea eliminar.

        pk : str
            Nombre del estilo (sin `workspace:`).

        Respuestas
        ----------
        HTTP 200
            Estilo eliminado correctamente.

        HTTP 400
            - Se intentó eliminar el estilo por defecto.
            - El estilo no estaba asociado al layer.

        HTTP 404
            El estilo no existe en GeoServer (caso raro dado que primero se consulta el layer).

        HTTP 502
            - No se pudo actualizar el XML del layer.
            - GeoServer rechazó el DELETE.

        Notas
        -----
        - El método siempre elimina usando `purge=true`.
        - Usa el formato extendido del layer, modificando explícitamente el XML.
        - Esta operación no afecta estilos globales de otros workspaces.
        """

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
        Cambia el estilo por defecto del layer asociado al dataset.

        Funcionalidad
        -------------
        Este endpoint establece un nuevo estilo SLD como estilo por defecto
        (defaultStyle) del layer en GeoServer.

        Reglas y validaciones
        ---------------------
        1. El estilo solicitado **debe estar asociado al layer**, ya sea como:
             - estilo listado en `<styles>`
             - o el actual estilo por defecto

        2. Si el estilo solicitado no está asociado, se responde con error 400.

        3. El método ajusta correctamente el XML del layer:
             - Mueve el default anterior a `<styles>` si no estaba ahí
             - Remueve el nuevo default de `<styles>` si estaba ahí
             - Actualiza el nodo `<defaultStyle>`

        Flujo interno
        -------------
        1. Verifica permisos con `_check_edit_perm`.
        2. Obtiene el XML del layer:
             GET /rest/layers/<layer>.xml
        3. Construye el nombre extendido: `<workspace>:<estilo>`
        4. Verifica que el estilo exista dentro del conjunto de estilos asociados.
        5. Actualiza:
             - `<styles>`
             - `<defaultStyle>`
        6. Envía el update por:
             PUT /rest/layers/<layer>.xml

        Parámetros
        ----------
        request : Request
            Debe incluir:
            {
                "style": "<nombre_estilo>"
            }

        dataset_pk : int
            ID del dataset cuyo estilo por defecto se modificará.

        Respuestas
        ----------
        HTTP 200
            Estilo por defecto actualizado correctamente.

        HTTP 400
            - No se envió `style` en el body.
            - El estilo no está asociado al dataset.

        HTTP 500
            Error inesperado de GeoServer al actualizar el XML.

        Notas
        -----
        - Esta operación **no crea ni elimina** estilos; solo cambia el default.
        - El estilo solicitado debe existir previamente y estar asociado.
        - Mantiene la estructura correcta del modo extendido de GeoServer.
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
