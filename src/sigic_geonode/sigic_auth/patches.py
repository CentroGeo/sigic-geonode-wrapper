from rest_framework.views import APIView
import logging
import re
import types

log = logging.getLogger(__name__)
_PATCHED = False
_PATCHED_AUTH_HEADER = False


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


def patch_get_token_from_auth_header():
    """
    Monkeypatch de geonode.base.auth.get_token_from_auth_header
    para "promocionar" Bearer JWT de Keycloak a token interno de GeoNode,
    reusando KeycloakJWTAuthentication.authenticate (sin duplicar lógica).
    """
    global _PATCHED_AUTH_HEADER
    if _PATCHED_AUTH_HEADER:
        return
    _PATCHED_AUTH_HEADER = True

    # Import tardío para no romper si GeoNode cambia orden de carga
    from geonode.base import auth as geonode_base_auth
    from geonode.base.auth import get_auth_token, get_or_create_token

    _orig = geonode_base_auth.get_token_from_auth_header

    def _looks_like_keycloak_accesstoken(token: str) -> bool:
        # Evita hacer red si claramente no es JWT: debe tener 2 puntos
        return token.count(".") == 2

    def _patched(auth_header, create_if_not_exists: bool = False):
        # Mantener compatibilidad exacta de firma y comportamiento
        if not auth_header:
            return None

        # Si no es Bearer, deferimos al original (maneja Basic y "otros")
        if not re.search(r"\bBearer\b", auth_header, re.IGNORECASE):
            return _orig(auth_header, create_if_not_exists)

        # Extraer el "raw token" (como hacía el original)
        raw = re.compile(re.escape("Bearer "), re.IGNORECASE).sub("", auth_header).strip()

        # Intento de promoción SOLO si parece JWT (header.payload.signature)
        if _looks_like_keycloak_accesstoken(raw):
            try:
                # Import tardío para evitar ciclos:
                from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

                # Construimos un "request" mínimo para llamar a tu authenticate()
                fake_req = types.SimpleNamespace(headers={"Authorization": f"Bearer {raw}"})
                user_auth_tuple = KeycloakJWTAuthentication().authenticate(fake_req)

                if user_auth_tuple:
                    # Tu authenticate() devuelve (user, None)
                    user, _ = user_auth_tuple
                    if user and getattr(user, "is_active", True):
                        # Convertimos el usuario en token interno de GeoNode
                        return get_auth_token(user) if not create_if_not_exists else get_or_create_token(user)

            except Exception as e:
                # Si falló la verificación OIDC, no rompemos compatibilidad:
                # seguimos con el comportamiento original (devuelve el token raw)
                log.debug("[sigic_auth] Keycloak bearer promotion failed, falling back: %s", e)

        # No parece JWT o no pasó validación → comportamiento original
        return _orig(auth_header, create_if_not_exists)

    # Aplicar el parche
    geonode_base_auth.get_token_from_auth_header = _patched
    log.info("[sigic_auth] Patched geonode.base.auth.get_token_from_auth_header")