from django.contrib.auth import get_user
from django.contrib.auth.models import AnonymousUser
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.functional import SimpleLazyObject
from rest_framework.exceptions import AuthenticationFailed

from .keycloak import KeycloakJWTAuthentication

# Middleware para saltarse CSRF si viene Authorization Bearer


class SkipCSRFMiddlewareForJWT(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Marcar como CSRF-exempt para que no falle, pero seguir procesando todo lo demás
            setattr(request, "_dont_enforce_csrf_checks", True)
        return super().process_view(request, callback, callback_args, callback_kwargs)


def _resolve_user(request):
    """
    Respeta sesión si existe. Si no, intenta Bearer con tu KeycloakJWTAuthentication.
    Nunca revienta la request: si el token no sirve, deja AnonymousUser.
    """
    # Si AuthenticationMiddleware ya autenticó por sesión, respétalo
    user = get_user(request)
    if getattr(user, "is_authenticated", False):
        return user

    # Intentar Bearer solo si hay header
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if auth.startswith("Bearer "):
        authenticator = KeycloakJWTAuthentication()
        try:
            result = authenticator.authenticate(request)
            if result:
                user, auth_obj = result  # tu clase devuelve (user, None)
                # Guarda opcionalmente el auth/claims si quieres reenviar downstream
                request.auth = auth_obj
                # Marca el usuario como cacheado para APIs de Django
                request._cached_user = user
                return user
        except AuthenticationFailed:
            # Token inválido → no autenticar, dejar anónimo
            pass
        except Exception:
            # Cualquier otra cosa, no bloquees vistas normales
            pass

    # Sin sesión ni token válido → anónimo
    return AnonymousUser()


class KeycloakUserFromBearerInjectionMiddleware:
    """
    Inyecta request.user si viene Authorization: Bearer ... válido.
    Colócala DESPUÉS de AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Reemplazamos request.user por un lazy que resuelve con sesión o Bearer
        request.user = SimpleLazyObject(lambda: _resolve_user(request))
        return self.get_response(request)
