import requests
from django.conf import settings
from geonode.layers.models import Dataset, LayerStyle


def upload_sld_to_geoserver(
    dataset_name: str, sld_name: str, sld_body: str, is_default=False
):
    """
    Sube un estilo SLD a GeoServer y lo asocia al layer indicado.
    Si el estilo ya existe, lo actualiza.
    """
    base_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
    user = settings.OGC_SERVER["default"]["USER"]
    password = settings.OGC_SERVER["default"]["PASSWORD"]

    # 1️⃣ Subir el estilo
    style_url = f"{base_url}/rest/styles"
    headers = {"Content-Type": "application/vnd.ogc.sld+xml"}

    # Crear o actualizar el estilo
    resp = requests.post(
        f"{style_url}?name={sld_name}",
        auth=(user, password),
        data=sld_body.encode("utf-8"),
        headers=headers,
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        if "already exists" in resp.text:
            # Actualizar si ya existía
            requests.put(
                f"{style_url}/{sld_name}",
                auth=(user, password),
                data=sld_body.encode("utf-8"),
                headers=headers,
                timeout=30,
            )
        else:
            raise Exception(
                f"Error subiendo estilo a GeoServer: {resp.status_code} {resp.text}"
            )

    # 2️⃣ Asociarlo con el layer
    layer_url = f"{base_url}/rest/layers/{dataset_name}.json"
    layer_resp = requests.get(layer_url, auth=(user, password))
    if layer_resp.status_code != 200:
        raise Exception(f"No se encontró la capa {dataset_name} en GeoServer")

    layer_data = layer_resp.json()["layer"]
    if "styles" not in layer_data:
        layer_data["styles"] = {"style": []}

    # Evitar duplicados
    if not any(s["name"] == sld_name for s in layer_data["styles"]["style"]):
        layer_data["styles"]["style"].append({"name": sld_name})

    # Si se pide como default, actualizarlo
    if is_default:
        layer_data["defaultStyle"] = {"name": sld_name}

    requests.put(
        layer_url,
        auth=(user, password),
        json={"layer": layer_data},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    return f"{base_url}/styles/{sld_name}.sld"


def sync_sld_with_geonode(
    dataset_name: str, sld_name: str, sld_url: str, is_default=False
):
    """
    Crea o actualiza el registro del estilo dentro de GeoNode y lo asocia al Dataset.
    """
    dataset = Dataset.objects.get(alternate=dataset_name)

    # Si este será el nuevo estilo por defecto, desmarcar los anteriores
    if is_default:
        dataset.styles.update(is_default=False)
        dataset.default_style = None

    style, _ = LayerStyle.objects.get_or_create(
        dataset=dataset,
        name=sld_name,
        defaults={"sld_url": sld_url, "is_default": is_default},
    )

    if is_default:
        style.is_default = True
        style.save()
        dataset.default_style = style
        dataset.save(update_fields=["default_style"])

    return style


def list_styles(dataset_name: str):
    """
    Devuelve todos los estilos registrados en GeoNode para un dataset.
    """
    dataset = Dataset.objects.get(alternate=dataset_name)
    styles = dataset.styles.all().order_by("-is_default", "name")
    return [
        {"name": s.name, "sld_url": s.sld_url, "is_default": s.is_default}
        for s in styles
    ]


def delete_style(dataset_name: str, style_name: str):
    """
    Elimina un estilo SLD de GeoServer y su registro en GeoNode.
    """
    base_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
    user = settings.OGC_SERVER["default"]["USER"]
    password = settings.OGC_SERVER["default"]["PASSWORD"]

    # 1️⃣ Eliminar del catálogo de GeoServer
    resp = requests.delete(
        f"{base_url}/rest/styles/{style_name}?purge=true",
        auth=(user, password),
        timeout=15,
    )
    if resp.status_code not in (200, 202, 204, 404):
        raise Exception(
            f"Error al eliminar estilo en GeoServer: {resp.status_code} {resp.text}"
        )

    # 2️⃣ Eliminar de la base de datos de GeoNode
    dataset = Dataset.objects.get(alternate=dataset_name)
    LayerStyle.objects.filter(dataset=dataset, name=style_name).delete()

    return True


def set_default_style(dataset_name: str, style_name: str):
    """
    Marca un estilo como predeterminado en GeoServer y GeoNode.
    """
    base_url = settings.OGC_SERVER["default"]["LOCATION"].rstrip("/")
    user = settings.OGC_SERVER["default"]["USER"]
    password = settings.OGC_SERVER["default"]["PASSWORD"]

    # 1️⃣ Actualizar en GeoServer
    layer_url = f"{base_url}/rest/layers/{dataset_name}.json"
    resp = requests.get(layer_url, auth=(user, password))
    if resp.status_code != 200:
        raise Exception(f"No se encontró la capa {dataset_name} en GeoServer")

    layer_json = resp.json()["layer"]
    layer_json["defaultStyle"] = {"name": style_name}

    put = requests.put(
        layer_url,
        auth=(user, password),
        headers={"Content-Type": "application/json"},
        json={"layer": layer_json},
        timeout=30,
    )

    if put.status_code not in (200, 201):
        raise Exception(
            f"Error al actualizar estilo por defecto en GeoServer: {put.status_code} {put.text}"
        )

    # 2️⃣ Actualizar en GeoNode
    dataset = Dataset.objects.get(alternate=dataset_name)
    dataset.styles.update(is_default=False)

    try:
        new_style = dataset.styles.get(name=style_name)
        new_style.is_default = True
        new_style.save()
        dataset.default_style = new_style
        dataset.save(update_fields=["default_style"])
    except LayerStyle.DoesNotExist:
        raise Exception(
            f"El estilo '{style_name}' no está registrado en GeoNode para el dataset '{dataset_name}'."
        )

    return new_style
