# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este codigo fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene credito de autoria, pero la titularidad del codigo
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

"""
URLs para mapas.

Registra los ViewSets en el router central y agrega
el endpoint de subida de imagenes como path directo.
"""

from django.urls import path

from sigic_geonode.router import router

from .views import (
    ImageUploadView,
    SigicMapViewSet,
    MapLayerViewSet,
)

# Registrar ViewSets en el router central
router.register(r"api/v2/sigic-maps", SigicMapViewSet, basename="sigic-maps")
router.register(r"api/v2/sigic-map-layers", MapLayerViewSet, basename="sigic-map-layers")

# Endpoint adicional para subida de imagenes (no es un ViewSet)
urlpatterns = [
    path(
        "api/v2/sigic-maps/upload/image",
        ImageUploadView.as_view(),
        name="sigic-map-upload-image",
    ),
]
