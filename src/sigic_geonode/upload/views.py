from importer.api.views import ImporterViewSet
from geonode.documents.api.views import DocumentViewSet
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

# 


class SigicImporterViewSet(ImporterViewSet):
    authentication_classes = [
        BasicAuthentication,
        SessionAuthentication,
        OAuth2Authentication,
        KeycloakJWTAuthentication,  
    ]


class SigicDocumentViewSet(DocumentViewSet):
    def get_authenticators(self):
        from rest_framework.authentication import BasicAuthentication, SessionAuthentication
        from oauth2_provider.contrib.rest_framework import OAuth2Authentication
        from sigic_geonode.sigic_auth.keycloak import KeycloakJWTAuthentication

        print("✅ get_authenticators personalizado en uso")

        return [
            BasicAuthentication(),
            SessionAuthentication(),
            OAuth2Authentication(),
            KeycloakJWTAuthentication(),
        ]
