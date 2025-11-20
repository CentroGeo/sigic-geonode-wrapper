# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

import re

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from geonode.base import auth as gba

from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

try:
    from geonode.base.auth import basic_auth_authenticate_user
except Exception:  # pragma: no cover
    basic_auth_authenticate_user = None


def _scheme(auth_header: str):
    if not auth_header:
        return None
    if re.search(r"\bBasic\b", auth_header, re.I):
        return "Basic"
    if re.search(r"\bBearer\b", auth_header, re.I):
        return "Bearer"
    return None


def _extract_bearer(auth_header: str) -> str:
    return (
        re.compile(re.escape("Bearer "), re.IGNORECASE)
        .sub("", auth_header or "")
        .strip()
    )


def _is_jwt(tok: str) -> bool:
    return bool(tok) and tok.count(".") == 2


def _token_value(x):
    """
    Normaliza lo que nos devuelva el core a un string:
    - AccessToken (DOT) -> x.token
    - dict con 'token' -> dict['token']
    - bytes -> decode
    - str -> tal cual
    - otro -> None (o str(x) si prefieres ver algo)
    """
    if x is None:
        return None
    try:
        # django-oauth-toolkit AccessToken
        if hasattr(x, "token"):
            return x.token
        if isinstance(x, dict) and "token" in x:
            return x["token"]
        if isinstance(x, (bytes, bytearray)):
            return x.decode("utf-8", errors="ignore")
        if isinstance(x, str):
            return x
        # último recurso: representar
        return str(x)
    except Exception:
        return None


def _summarize_token(tok: str, full: bool = False):
    if not tok:
        return None
    if full:
        return tok
    if len(tok) <= 16:
        return f"{tok} (len={len(tok)})"
    return f"{tok[:8]}...{tok[-6:]} (len={len(tok)})"


@csrf_exempt
def whoami(request):
    """
    /sigic-auth/whoami[?verbose=1]
    - Basic -> token interno (crea si no existe)
    - Bearer (JWT Keycloak válido) -> token interno (promoción)
    - Bearer (no-JWT / token interno) -> se devuelve tal cual
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

    if not auth_header:
        out["flow"] = "none"
        out["details"]["note"] = "No llegó Authorization (revisa proxy)."
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

            core_res = gba.get_token_from_auth_header(
                auth_header, create_if_not_exists=True
            )
            tok = _token_value(core_res)
            out["flow"] = "basic->internal"
            out["details"]["token_internal"] = _summarize_token(tok, full=verbose)
            return JsonResponse(out)

        if scheme == "Bearer":
            raw = _extract_bearer(auth_header)
            out["details"]["bearer_is_jwt_format"] = _is_jwt(raw)
            out["details"]["bearer_raw"] = _summarize_token(raw, full=verbose)

            kc_user = None
            try:
                kc_res = KeycloakJWTAuthentication().authenticate(request)
                if kc_res:
                    kc_user, _ = kc_res
            except Exception as e:
                out["details"]["keycloak_error"] = str(e)

            if kc_user:
                out["details"]["keycloak_user"] = getattr(kc_user, "username", None)
                promoted = gba.get_token_from_auth_header(
                    auth_header, create_if_not_exists=True
                )
                tok = _token_value(promoted)
                out["flow"] = "keycloak->internal"
                out["details"]["token_internal"] = _summarize_token(tok, full=verbose)
                return JsonResponse(out)

            # Compatibilidad: si no autentica como Keycloak, devolvemos lo que el core diga
            core_res = gba.get_token_from_auth_header(
                auth_header, create_if_not_exists=False
            )
            core_tok = _token_value(core_res)
            out["details"]["core_result"] = _summarize_token(core_tok, full=verbose)
            out["flow"] = "bearer->raw" if core_tok == raw else "bearer->core_result"
            return JsonResponse(out)

        out["flow"] = "none"
        out["details"]["note"] = "Esquema no reconocido."
        return JsonResponse(out)

    except Exception as e:
        out["flow"] = "error"
        out["details"]["exception"] = str(e)
        return JsonResponse(out, status=500)
