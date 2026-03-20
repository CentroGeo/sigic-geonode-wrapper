# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este codigo fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene credito de autoria, pero la titularidad del codigo
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
Permisos personalizados para mapas.

Implementa la cadena de propiedad:
  MapLayer -> SigicMap -> owner
"""

from rest_framework import permissions

from .models import SigicMap, MapLayer


class IsMapOwner(permissions.BasePermission):
    """
    Verifica que el usuario autenticado sea el propietario del mapa.

    Recorre la cadena de relaciones para objetos hijos
    (MapLayer) hasta llegar al SigicMap
    y comparar su owner con request.user.

    Para metodos de solo lectura (GET, HEAD, OPTIONS) permite el
    acceso a mapas publicos sin autenticacion.
    """

    def has_object_permission(self, request, view, obj):
        sigic_map = self._get_sigic_map(obj)
        if sigic_map is None:
            return False

        # Lectura permitida
        if request.method in permissions.SAFE_METHODS:
            return True

        # Escritura requiere ser el propietario
        return request.user.is_authenticated and sigic_map.owner == request.user

    @staticmethod
    def _get_sigic_map(obj):
        """Obtiene el SigicMap raiz a partir de cualquier objeto de la jerarquia."""
        if isinstance(obj, SigicMap):
            return obj
        if isinstance(obj, MapLayer):
            return obj.map
        return None
