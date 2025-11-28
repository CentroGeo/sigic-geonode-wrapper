# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Colaboradores: Fernando Valle
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

from .views import (
    ResourceKeywordTagViewSet,
    SigicResourceBaseViewSet,
    SigicResourceShortViewSet,
)

urlpatterns = []

router.register(
    r"api/v2/sigic-resources", SigicResourceBaseViewSet, basename="sigic-resources"
)
router.register(
    r"api/v2/sigic-resources-short",
    SigicResourceShortViewSet,
    basename="sigic-resources-short",
)

router.register(
    r"api/v2/resources/(?P<resource_pk>[^/.]+)/keywordtags",
    ResourceKeywordTagViewSet,
    basename="sigic-resources-keywords",
)
