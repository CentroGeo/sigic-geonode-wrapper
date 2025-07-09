from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from jose import jwt, jwk
from jose.utils import base64url_decode
import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required as original_login_required
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from functools import wraps
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError
import os



SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER = os.getenv('SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER', 'https://iam.dev.geoint.mx/realms/sigic')
JWKS_URL = f"{SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER}/protocol/openid-connect/certs"


class KeycloakJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        try:
            jwks = requests.get(JWKS_URL).json()
            unverified_header = jwt.get_unverified_header(token)

            print("Header del token:", unverified_header)

            key = next(k for k in jwks['keys'] if k['kid'] == unverified_header['kid'])
            public_key = jwk.construct(key)

            message, encoded_signature = token.rsplit('.', 1)
            decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

            if not public_key.verify(message.encode("utf8"), decoded_signature):
                raise AuthenticationFailed('Firma inválida')

            payload = jwt.decode(
                token,
                public_key,
                algorithms=[key['alg']],
                audience="account",
                issuer=SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER
            )

            print("Payload decodificado:", payload)

            if 'preferred_username' not in payload:
                raise AuthenticationFailed("Token válido pero sin 'preferred_username'")

            User = get_user_model()
            user, _ = User.objects.get_or_create(username=payload['preferred_username'])
            return (user, None)

        except (ExpiredSignatureError, JWTClaimsError, JWTError, Exception) as e:
            print("Excepción al autenticar:", e)
            raise AuthenticationFailed(f'Token inválido: {str(e)}')


class KeycloakJWTAuthenticationBak(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        try:
            # Obtener las claves públicas de Keycloak (JWKs)
            jwks = requests.get(JWKS_URL).json()
            unverified_header = jwt.get_unverified_header(token)

            # Buscar la clave con el kid correcto
            key = next(k for k in jwks['keys'] if k['kid'] == unverified_header['kid'])
            public_key = jwk.construct(key)

            # Verificar la firma manualmente (opcional, solo si quieres validar antes de decodificar)
            message, encoded_signature = token.rsplit('.', 1)
            decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

            if not public_key.verify(message.encode("utf8"), decoded_signature):
                raise AuthenticationFailed('Firma inválida')

            unverified_payload = jwt.get_unverified_claims(token)
            print(unverified_payload)

            # Decodificar el token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[key['alg']],
                audience="account",
                issuer=SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER
            )

            # Crear o recuperar usuario en Django
            User = get_user_model()
            user, _ = User.objects.get_or_create(username=payload['preferred_username'])
            return (user, None)

        except Exception as e:
            raise AuthenticationFailed(f'Token inválido: {str(e)}')


def jwt_or_session_login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Monkeypatch para login_required que acepta JWT o sesión.
    Compatible con FBV y CBV (@method_decorator).
    """

    def check_auth(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            try:
                auth = KeycloakJWTAuthentication()
                user_auth_tuple = auth.authenticate(request)
                if user_auth_tuple:
                    user, _ = user_auth_tuple
                    request.user = user
                    # return csrf_exempt(view_func)(request, *args, **kwargs)
                    setattr(request, '_dont_enforce_csrf_checks', True)
                    return view_func(request, *args, **kwargs)
            except Exception as e:
                return JsonResponse({"detail": f"Token inválido: {str(e)}"}, status=401)

            # fallback: redirige como lo haría login_required
            actual_decorator = user_passes_test(
                lambda u: u.is_authenticated,
                login_url=login_url,
                redirect_field_name=redirect_field_name,
            )
            return actual_decorator(view_func)(request, *args, **kwargs)

        return _wrapped_view

    if function:
        return check_auth(function)

    return check_auth

