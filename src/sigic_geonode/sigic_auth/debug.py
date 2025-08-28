from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from geonode.base import auth as gba
from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

import re

# Opcional: si quieres ver también el usuario resuelto por Basic
try:
    from geonode.base.auth import basic_auth_authenticate_user
except Exception:  # pragma: no cover
    basic_auth_authenticate_user = None


def _summarize_token(tok: str, full: bool = False):
    if not tok:
        return None
    if full:
        return tok
    # máscara segura por defecto
    return f"{tok[:8]}...{tok[-6:]} (len={len(tok)})"


def _is_jwt(tok: str) -> bool:
    # formato típico header.payload.signature
    return bool(tok) and tok.count(".") == 2


def _extract_bearer(auth_header: str) -> str:
    return re.compile(re.escape("Bearer "), re.IGNORECASE).sub("", auth_header or "").strip()


def _scheme(auth_header: str):
    if not auth_header:
        return None
    if re.search(r"\bBasic\b", auth_header, re.I):
        return "Basic"
    if re.search(r"\bBearer\b", auth_header, re.I):
        return "Bearer"
    return None


@csrf_exempt
def whoami(request):
    """
    Endpoint de depuración:
    - Detecta esquema (Basic / Bearer)
    - Ejecuta el mismo flujo lógico que tu parche:
        * Basic -> token interno
        * Bearer JWT Keycloak válido -> token interno
        * Bearer no-JWT (token interno OAuth Toolkit) -> retorno sin cambios
    - Reporta el "flow" seguido y el módulo de la función parcheada
    """
    auth_header = request.headers.get("Authorization", "")
    scheme = _scheme(auth_header)
    verbose = request.GET.get("verbose") in ("1", "true", "yes")
    out = {
        "patched_module": getattr(gba.get_token_from_auth_header, "__module__", None),
        "request_user": {
            "is_authenticated": bool(getattr(request.user, "is_authenticated", False)),
            "username": getattr(request.user, "username", None),
        },
        "auth_header_present": bool(auth_header),
        "scheme": scheme,
        "flow": None,
        "details": {},
    }

    # Si no hay cabecera Authorization, devolvemos pronto
    if not auth_header:
        out["details"]["note"] = "No llegó cabecera Authorization (revisa proxy)."
        return JsonResponse(out)

    try:
        if scheme == "Basic":
            # Opcional: comprobar qué usuario resuelve Basic
            if basic_auth_authenticate_user:
                try:
                    u = basic_auth_authenticate_user(auth_header)
                    if u:
                        out["details"]["basic_user"] = getattr(u, "username", None)
                except Exception as e:
                    out["details"]["basic_error"] = str(e)

            # Obtenemos token interno como hace el core (equivalente a tu parche)
            tok = gba.get_token_from_auth_header(auth_header, create_if_not_exists=True)
            out["flow"] = "basic->internal"
            out["details"]["token_internal"] = _summarize_token(tok, full=verbose)
            return JsonResponse(out)

        if scheme == "Bearer":
            raw = _extract_bearer(auth_header)
            out["details"]["bearer_is_jwt_format"] = _is_jwt(raw)
            out["details"]["bearer_raw"] = _summarize_token(raw, full=verbose)

            # Intento Keycloak (como en el parche): si autentica -> promovemos a token interno
            kc_user = None
            try:
                kc_res = KeycloakJWTAuthentication().authenticate(request)
                if kc_res:
                    kc_user, _ = kc_res
            except Exception as e:
                out["details"]["keycloak_error"] = str(e)

            if kc_user:
                out["details"]["keycloak_user"] = getattr(kc_user, "username", None)
                promoted = gba.get_token_from_auth_header(auth_header, create_if_not_exists=True)
                out["flow"] = "keycloak->internal"
                out["details"]["token_internal"] = _summarize_token(promoted, full=verbose)
                return JsonResponse(out)

            # Si no autentica como Keycloak, seguimos el comportamiento original:
            # Para tokens internos (no-JWT), el core devuelve el token tal cual.
            core_token = gba.get_token_from_auth_header(auth_header, create_if_not_exists=False)
            out["details"]["core_result"] = _summarize_token(core_token, full=verbose)
            # Heurística del flujo:
            if core_token == raw:
                out["flow"] = "bearer->raw"
            else:
                # Inusual, pero por si algún backend cambiara el valor.
                out["flow"] = "bearer->core_result"
            return JsonResponse(out)

        # Esquema desconocido o ausente
        out["flow"] = "none"
        out["details"]["note"] = "Esquema no reconocido (ni Basic ni Bearer)."
        return JsonResponse(out)

    except Exception as e:
        out["flow"] = "error"
        out["details"]["exception"] = str(e)
        return JsonResponse(out, status=500)
