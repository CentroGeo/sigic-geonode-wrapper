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

"""
URLs para servicios remotos.

Este módulo:
1. Aplica monkey patches a HarvesterViewSet de GeoNode
2. Registra ServiceViewSet en el router (nuevo endpoint /api/v2/services/)
3. Registra RemoteDatasetViewSet con filtros por harvester_id y service_id
"""

from sigic_geonode.router import router

# Importar patches para aplicarlos al cargar el módulo
from . import patches  # noqa: F401

from .views import ServiceViewSet, RemoteDatasetViewSet

urlpatterns = []

# Servicios remotos (nuevo endpoint que GeoNode no tiene)
router.register(
    r"api/v2/services",
    ServiceViewSet,
    basename="services",
)

# Datasets con filtros por harvester_id y service_id
router.register(
    r"api/v2/sigic-remote-datasets",
    RemoteDatasetViewSet,
    basename="sigic-remote-datasets",
)
