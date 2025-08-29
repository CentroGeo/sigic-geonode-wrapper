from django.apps import AppConfig
from django.conf import settings

class SigicAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sigic_geonode.sigic_auth'

    def ready(self):
        # Solo activar si el flag está prendido
        use_oidc = getattr(settings, "SOCIALACCOUNT_OIDC_PROVIDER_ENABLED", False)
        if not use_oidc:
            print("[geonode_keycloak] OIDC deshabilitado. No se aplicarán parches.")
            return

        # 1) Parche para añadir authenticator keycloak en DRF
        from .patches import patch_drf_get_authenticators
        patch_drf_get_authenticators()
        print("[geonode_keycloak] OIDC habilitado. Parche get_authenticators() aplicado.")

        # 2) Parche para get_token_from_auth_header para promover Bearer token keycloak a token GeoNode
        from .patches import patch_get_token_from_auth_header
        patch_get_token_from_auth_header()
        print("[geonode_keycloak] OIDC habilitado. Parche get_token_from_auth_header() aplicado.")

        # 3) asegura que el header downstream sea el interno de GeoNode
        from .patches import patch_proxy_authorization_header
        patch_proxy_authorization_header()
        print("[geonode_keycloak] OIDC habilitado. Parche proxy_authorization_header() aplicado.")