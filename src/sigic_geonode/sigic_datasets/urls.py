# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

from sigic_geonode.router import router

from .views import DatasetKeywordsViewSet

urlpatterns = []

router.register(
    r"api/v2/datasets/(?P<dataset_pk>[^/.]+)/keywordtags",
    DatasetKeywordsViewSet,
    basename="datasets-keywords",
)
