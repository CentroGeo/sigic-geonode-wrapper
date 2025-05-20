from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from jose import jwt, jwk
from jose.utils import base64url_decode
import requests
from django.contrib.auth import get_user_model

KEYCLOAK_REALM = 'sigic'
KEYCLOAK_SERVER_URL = 'https://iam.sigic.dev.cesarbenjamin.net'
KEYCLOAK_CLIENT_ID = 'sigic_geonode'

JWKS_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
ISSUER = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"

class KeycloakJWTAuthentication(BaseAuthentication):
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
                issuer=ISSUER
            )

            # Crear o recuperar usuario en Django
            User = get_user_model()
            user, _ = User.objects.get_or_create(username=payload['preferred_username'])
            return (user, None)

        except Exception as e:
            raise AuthenticationFailed(f'Token inválido: {str(e)}')

