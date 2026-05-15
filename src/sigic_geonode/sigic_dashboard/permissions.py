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
        if request.user.is_staff:
            return True
        # obj puede ser Site directamente o un objeto con FK a site
        site = obj if hasattr(obj, "owner_id") else getattr(obj, "site", None)
        if site is None:
            return True  # sin site asociado, permitir (control en has_permission)
        return site.owner_id == request.user.pk
