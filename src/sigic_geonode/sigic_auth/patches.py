from rest_framework.views import APIView

_PATCHED = False


def patch_drf_get_authenticators():
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    # Import tardío para evitar ciclos
    from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

    _orig_get_authenticators = APIView.get_authenticators

    def _patched_get_authenticators(self):
        """
        Añade KeycloakJWTAuthentication a la lista devuelta por DRF,
        sin duplicar y con posibilidad de excluir por vista:
          class MiVista(...):
              disable_auto_keycloak = True
        """
        authenticators = list(_orig_get_authenticators(self))

        # Opt-out por vista
        if getattr(self, "disable_auto_keycloak", False):
            return authenticators

        # Evitar duplicados
        if any(isinstance(a, KeycloakJWTAuthentication) for a in authenticators):
            return authenticators

        # Solo añadir si la vista ya tenía algún autenticador (no alterar vistas públicas)
        if len(authenticators) > 0:
            authenticators.append(KeycloakJWTAuthentication())

        return authenticators

    APIView.get_authenticators = _patched_get_authenticators