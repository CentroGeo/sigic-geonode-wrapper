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
    Permiso extensible para operaciones administrativas del dashboard.

    Stub: actualmente equivale a IsAuthenticated. Extender segun roles
    cuando se definan grupos de administracion de sitios.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
