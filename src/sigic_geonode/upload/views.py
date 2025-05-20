from importer.api.views import ImporterViewSet
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from sigic_geonode.auth.keycloak import KeycloakJWTAuthentication

class SigicImporterViewSet(ImporterViewSet):
    authentication_classes = [
        BasicAuthentication,
        SessionAuthentication,
        OAuth2Authentication,
        KeycloakJWTAuthentication,  
    ]
