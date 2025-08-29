from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from geonode.base import auth as gba
from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

import re
import time
from jose import jwt

try:
    from geonode.base.auth import basic_auth_authenticate_user
except Exception:  # pragma: no cover
    basic_auth_authenticate_user = None


def _coerce_token_str(tok):
    """
    Acepta strings, DOT AccessToken (tiene .token), DRF Token (tiene .key), etc.
    Devuelve str o None.
    """
    if tok is None:
        return None
    if isinstance(tok, str):
        return tok
    for attr in ("token", "key", "access_token", "value"):
        val = getattr(tok, attr, None)
        if isinstance(val, str):
            return val
    # último recurso: str()
    try:
        s = str(tok)
        # evita representar objetos enormes/verbosos
        return s if len(s) < 2048 else s[:2048]
    except Exception:
        return f"<{tok.__class__.__name__}>"


def _summarize_token(tok: str, full: bool = False):
    if not tok:
        return None
    if full:
        return tok
    return f"{tok[:8]}...{tok[-6:]} (len={len(tok)})"


def _is_jwt(tok: str) -> bool:
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

    if not auth_header:
        out["details"]["note"] = "No llegó cabecera Authorization (revisa proxy)."
        return JsonResponse(out)

    try:
        if scheme == "Basic":
            if basic_auth_authenticate_user:
                try:
                    u = basic_auth_authenticate_user(auth_header)
                    if u:
                        out["details"]["basic_user"] = getattr(u, "username", None)
                except Exception as e:
                    out["details"]["basic_error"] = str(e)

            tok_obj = gba.get_token_from_auth_header(auth_header, create_if_not_exists=True)
            tok = _coerce_token_str(tok_obj)
            out["flow"] = "basic->internal"
            out["details"]["token_internal"] = _summarize_token(tok, full=verbose)
            out["details"]["token_type"] = tok_obj.__class__.__name__ if tok_obj is not None else None
            return JsonResponse(out)

        if scheme == "Bearer":
            raw = _extract_bearer(auth_header)
            out["details"]["bearer_raw"] = _summarize_token(raw, full=verbose)
            out["details"]["bearer_is_jwt_format"] = _is_jwt(raw)

            # Si parece JWT, mostramos claims sin verificar y hora actual para diagnosticar exp/iat
            if _is_jwt(raw):
                try:
                    unverified = jwt.get_unverified_claims(raw)
                    out["details"]["jwt_claims_unverified"] = {
                        "iss": unverified.get("iss"),
                        "aud": unverified.get("aud"),
                        "iat": unverified.get("iat"),
                        "exp": unverified.get("exp"),
                    }
                    out["details"]["now_epoch"] = int(time.time())
                    if unverified.get("exp"):
                        out["details"]["seconds_to_expiry"] = unverified["exp"] - int(time.time())
                except Exception as e:
                    out["details"]["jwt_unverified_error"] = str(e)

            # Intento Keycloak: si autentica, promovemos a token interno
            kc_user = None
            try:
                kc_res = KeycloakJWTAuthentication().authenticate(request)
                if kc_res:
                    kc_user, _ = kc_res
            except Exception as e:
                out["details"]["keycloak_error"] = str(e)

            if kc_user:
                out["details"]["keycloak_user"] = getattr(kc_user, "username", None)
                promoted_obj = gba.get_token_from_auth_header(auth_header, create_if_not_exists=True)
                promoted = _coerce_token_str(promoted_obj)
                out["flow"] = "keycloak->internal"
                out["details"]["token_internal"] = _summarize_token(promoted, full=verbose)
                out["details"]["token_type"] = promoted_obj.__class__.__name__ if promoted_obj is not None else None
                return JsonResponse(out)

            # Si no autentica con Keycloak, comportamiento original: para tokens internos, devuelve raw
            core_obj = gba.get_token_from_auth_header(auth_header, create_if_not_exists=False)
            core = _coerce_token_str(core_obj)
            out["details"]["core_result"] = _summarize_token(core, full=verbose)
            out["details"]["core_result_type"] = core_obj.__class__.__name__ if core_obj is not None else None

            out["flow"] = "bearer->raw" if core == raw else "bearer->core_result"
            return JsonResponse(out)

        out["flow"] = "none"
        out["details"]["note"] = "Esquema no reconocido (ni Basic ni Bearer)."
        return JsonResponse(out)

    except Exception as e:
        out["flow"] = "error"
        out["details"]["exception"] = str(e)
        return JsonResponse(out, status=500)
