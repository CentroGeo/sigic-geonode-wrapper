# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

# src/sigic_geonode/sigic_auth/utils.py

from .models import SigicRole, UserGroupRole


def user_admin_groups(user):
    """Retorna los IDs de los grupos donde el usuario es admin."""
    if user.is_superuser:
        return None  # None significa "todos"
    try:
        admin_role = SigicRole.objects.get(name="admin")
    except SigicRole.DoesNotExist:
        return []
    return UserGroupRole.objects.filter(user=user, role=admin_role).values_list(
        "group_id", flat=True
    )
