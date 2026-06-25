# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

from sigic_geonode.router import router

from .views import SigicDatasetMetadataImportViewSet

urlpatterns = []

router.register(
    r"api/v2/datasets/(?P<dataset_pk>[^/.]+)/metadata-import",
    SigicDatasetMetadataImportViewSet,
    basename="datasets-metadata-import",
)
