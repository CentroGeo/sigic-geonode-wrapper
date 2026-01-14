# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from sigic_geonode.router import router

from .views import RemoteServiceViewSet, RemoteDatasetViewSet

urlpatterns = []

router.register(
    r"api/v2/sigic-remote-services",
    RemoteServiceViewSet,
    basename="sigic-remote-services",
)

router.register(
    r"api/v2/sigic-remote-datasets",
    RemoteDatasetViewSet,
    basename="sigic-remote-datasets",
)
