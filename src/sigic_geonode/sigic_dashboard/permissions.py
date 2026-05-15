# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from rest_framework.permissions import BasePermission


class IsDashboardAdmin(BasePermission):
    """
    Permiso para operaciones administrativas del dashboard.
    Equivale a IsAuthenticated (control de propietario se delega a IsSiteOwner).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsSiteOwner(BasePermission):
    """
    Permite editar/eliminar un Site solo a su propietario o a staff.
    Para objetos relacionados (groups, indicators) verifica el site antecesor.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        # obj puede ser Site directamente o un objeto con FK a site
        site = obj if hasattr(obj, "owner_id") else getattr(obj, "site", None)
        if site is None:
            return True  # sin site asociado, permitir (control en has_permission)
        if site.owner_id is None:
            return True  # tablero legado sin propietario asignado
        return site.owner_id == user.pk
