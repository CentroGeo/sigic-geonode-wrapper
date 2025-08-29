from rest_framework.views import APIView
import logging

log = logging.getLogger('geonode')
_PATCHED = False
_PATCHED_AUTH_HEADER = False
_PATCHED_PROXY = False


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
    para 'promocionar' Bearer JWT de Keycloak a token interno de GeoNode,
    reutilizando KeycloakJWTAuthentication.authenticate().

    Comportamiento:
      - Basic            -> igual que el original (token interno; crea si se pide)
      - Bearer (JWT OK)  -> token interno (crea si se pide)
      - Bearer (no-JWT o inválido) -> igual que el original (raw token)
      - Sin header       -> None
    """
    import logging
    import re
    import types

    log = logging.getLogger("geonode.sigic_auth")
    global _PATCHED_AUTH_HEADER
    if _PATCHED_AUTH_HEADER:
        log.debug("[sigic_auth] get_token_from_auth_header ya estaba parcheado; skip")
        return
    _PATCHED_AUTH_HEADER = True

    from geonode.base import auth as geonode_base_auth
    from geonode.base.auth import get_auth_token, get_or_create_token

    _orig = geonode_base_auth.get_token_from_auth_header

    def _mask(tok: str, keep: int = 8) -> str:
        if not tok:
            return tok
        if len(tok) <= keep + 6:
            return f"{tok} (len={len(tok)})"
        return f"{tok[:keep]}...{tok[-6:]} (len={len(tok)})"

    def _extract_bearer(auth_header: str) -> str:
        return re.compile(re.escape("Bearer "), re.IGNORECASE).sub("", auth_header or "").strip()

    def _looks_like_jwt(token: str) -> bool:
        # Estructura JWT canónica: 3 partes no vacías separadas por puntos
        if not token:
            return False
        parts = token.split(".")
        return len(parts) == 3 and all(parts)

    class _FakeReq:
        """
        Fake request compatible con:
        - request.headers['Authorization']
        - request.META['HTTP_AUTHORIZATION']
        """
        def __init__(self, bearer: str):
            auth_value = f"Bearer {bearer}"
            # headers estilo Django request
            self.headers = {"Authorization": auth_value}
            # META estilo WSGI
            self.META = {"HTTP_AUTHORIZATION": auth_value}
            # por si el authenticator revisa cookies
            self.COOKIES = {}

    from functools import wraps

    @wraps(_orig)
    def _patched(auth_header, create_if_not_exists: bool = False):
        # 0) Sin header -> None (igual que original)
        if not auth_header:
            return None

        # 1) Basic -> delega al original (que ya crea token interno)
        if re.search(r"\bBasic\b", auth_header, re.IGNORECASE):
            return _orig(auth_header, create_if_not_exists)

        # 2) Bearer: intentamos promoción si parece JWT
        if re.search(r"\bBearer\b", auth_header, re.IGNORECASE):
            raw = _extract_bearer(auth_header)
            log.debug("[sigic_auth] get_token_from_auth_header: Bearer recibido (masked)=%s", _mask(raw))

            if _looks_like_jwt(raw):
                try:
                    # Import tardío para evitar ciclos
                    from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

                    fake_req = _FakeReq(raw)
                    res = KeycloakJWTAuthentication().authenticate(fake_req)
                    if res:
                        user, _ = res
                        if user and getattr(user, "is_active", True):
                            token_obj = (
                                get_auth_token(user)
                                if not create_if_not_exists
                                else get_or_create_token(user)
                            )
                            # Normalizar posibles tipos (objeto DOT u otros)
                            tok_val = getattr(token_obj, "token", None) or (
                                token_obj.get("token") if isinstance(token_obj, dict) else None
                            ) or (token_obj if isinstance(token_obj, str) else None)

                            log.debug(
                                "[sigic_auth] Promoción OK -> token interno (masked)=%s user=%s",
                                _mask(tok_val), getattr(user, "username", None)
                            )
                            return token_obj.token  # devolver el mismo tipo que usa GeoNode (objeto/dict/str)
                        else:
                            log.debug("[sigic_auth] authenticate() devolvió user inactivo o None")
                    else:
                        log.debug("[sigic_auth] authenticate() devolvió None")

                except Exception as e:
                    # Seguridad / compat: no romper llamadas existentes
                    log.debug("[sigic_auth] Promoción falló; fallback al original: %s", str(e), exc_info=False)

            # No parece JWT o promoción falló -> comportamiento original (raw)
            return _orig(auth_header, create_if_not_exists)

        # 3) Otros esquemas -> original
        return _orig(auth_header, create_if_not_exists)

    geonode_base_auth.get_token_from_auth_header = _patched
    log.info("[sigic_auth] Parche aplicado: geonode.base.auth.get_token_from_auth_header")
