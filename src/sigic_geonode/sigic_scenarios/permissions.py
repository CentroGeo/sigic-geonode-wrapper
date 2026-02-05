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
Permisos personalizados para escenarios.

Implementa la cadena de propiedad:
  SceneMarker / SceneLayer -> Scene -> Scenario -> owner
"""

from rest_framework import permissions

from .models import Scenario, Scene, SceneLayer, SceneMarker


class IsScenarioOwner(permissions.BasePermission):
    """
    Verifica que el usuario autenticado sea el propietario del escenario.

    Recorre la cadena de relaciones para objetos hijos
    (Scene, SceneLayer, SceneMarker) hasta llegar al Scenario
    y comparar su owner con request.user.

    Para metodos de solo lectura (GET, HEAD, OPTIONS) permite el
    acceso a escenarios publicos sin autenticacion.
    """

    def has_object_permission(self, request, view, obj):
        scenario = self._get_scenario(obj)
        if scenario is None:
            return False

        # Lectura permitida si el escenario es publico
        if request.method in permissions.SAFE_METHODS and scenario.is_public:
            return True

        # Escritura requiere ser el propietario
        return request.user.is_authenticated and scenario.owner == request.user

    @staticmethod
    def _get_scenario(obj):
        """Obtiene el Scenario raiz a partir de cualquier objeto de la jerarquia."""
        if isinstance(obj, Scenario):
            return obj
        if isinstance(obj, Scene):
            return obj.scenario
        if isinstance(obj, (SceneLayer, SceneMarker)):
            return obj.scene.scenario
        return None
