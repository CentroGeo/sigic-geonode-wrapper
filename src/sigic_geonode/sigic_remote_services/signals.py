# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

import re
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from geonode.layers.models import Dataset

from .models import RemoteLayerTypename

logger = logging.getLogger(__name__)

_SUFFIX_RE = re.compile(r"_h\d+$")


def _strip_harvester_suffix(alternate):
    """Elimina el sufijo _h{id} del typename: 'ws:name_h2' → 'ws:name'."""
    if not alternate:
        return alternate
    parts = alternate.split(":", 1)
    if len(parts) == 2:
        return f"{parts[0]}:{_SUFFIX_RE.sub('', parts[1])}"
    return _SUFFIX_RE.sub("", alternate)


_DEFAULT_KEYWORD = "Servicio remoto"

_ANONYMOUS_PERMS = [
    "view_resourcebase",
    "download_resourcebase",
]


def _revoke_anonymous_permissions(instance):
    """Revoca view/download de AnonymousUser y del grupo anonymous en Guardian."""
    try:
        from guardian.shortcuts import get_anonymous_user, remove_perm
        from django.contrib.auth.models import Group

        rb = instance.resourcebase_ptr
        anon_user = get_anonymous_user()
        anon_group = Group.objects.filter(name="anonymous").first()

        for perm in _ANONYMOUS_PERMS:
            remove_perm(f"base.{perm}", anon_user, rb)
            if anon_group:
                remove_perm(f"base.{perm}", anon_group, rb)
    except Exception as exc:
        logger.warning(
            "[SIGIC Signal] No se pudieron revocar permisos anónimos "
            "en dataset %s: %s",
            instance.pk,
            exc,
        )


def _set_remote_metadata_defaults(instance, created=False):
    """
    Puebla attribution, category, date_type y keywords si están vacíos en recursos REMOTE.

    En creación también fuerza is_published=False e is_approved=False para que el
    recurso sea privado hasta que el owner solicite publicación y un admin apruebe.

    Usa .update() para campos escalares (evita recursión de señal) y el manager
    de M2M para keywords (no dispara post_save en Dataset).
    """
    from geonode.base.models import TopicCategory

    updates = {}

    if not instance.attribution:
        updates["attribution"] = "Servicio remoto"

    if not instance.category_id:
        category = TopicCategory.objects.filter(identifier="externalCatalog").first()
        if category:
            updates["category_id"] = category.pk

    if not instance.date_type:
        updates["date_type"] = "publication"

    if created:
        updates["is_published"] = False
        updates["is_approved"] = False

    if created:
        _revoke_anonymous_permissions(instance)

    if updates:
        try:
            instance.__class__.objects.filter(pk=instance.pk).update(**updates)
            logger.debug(
                "[SIGIC Signal] Metadatos por defecto aplicados al dataset REMOTE %s: %s",
                instance.pk,
                list(updates.keys()),
            )
        except Exception as exc:
            logger.warning(
                "[SIGIC Signal] No se pudieron aplicar metadatos por defecto "
                "al dataset %s: %s",
                instance.pk,
                exc,
            )

    # keywords usa M2M — no dispara post_save, no hay recursión
    try:
        if not instance.keywords.exists():
            instance.keywords.add(_DEFAULT_KEYWORD)
    except Exception as exc:
        logger.warning(
            "[SIGIC Signal] No se pudo agregar keyword por defecto "
            "al dataset %s: %s",
            instance.pk,
            exc,
        )


@receiver(post_save, sender=Dataset, weak=False)
def sync_remote_typename(sender, instance, **kwargs):
    """Mantiene RemoteLayerTypename y metadatos mínimos sincronizados al guardar un Dataset remoto."""
    if instance.sourcetype != "REMOTE":
        return
    alternate = getattr(instance, "alternate", None)
    if not alternate:
        return

    real_typename = _strip_harvester_suffix(alternate)
    try:
        RemoteLayerTypename.objects.update_or_create(
            dataset=instance,
            defaults={"typename": real_typename},
        )
    except Exception as exc:
        logger.warning(
            "[SIGIC Signal] No se pudo guardar RemoteLayerTypename "
            "para dataset %s: %s",
            instance.pk,
            exc,
        )

    _set_remote_metadata_defaults(instance, created=kwargs.get("created", False))
