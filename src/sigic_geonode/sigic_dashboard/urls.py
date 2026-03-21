# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from sigic_geonode.router import router

from .views import (
    IndicatorFieldBoxInfoViewSet,
    IndicatorGroupViewSet,
    IndicatorViewSet,
    SiteConfigurationViewSet,
    SiteLogosViewSet,
    SiteViewSet,
    SubGroupViewSet,
)

router.register(r"api/v2/dashboard/sites", SiteViewSet, basename="dashboard-sites")
router.register(
    r"api/v2/dashboard/site-logos", SiteLogosViewSet, basename="dashboard-site-logos"
)
router.register(
    r"api/v2/dashboard/groups", IndicatorGroupViewSet, basename="dashboard-groups"
)
router.register(
    r"api/v2/dashboard/subgroups", SubGroupViewSet, basename="dashboard-subgroups"
)
router.register(
    r"api/v2/dashboard/indicators", IndicatorViewSet, basename="dashboard-indicators"
)
router.register(
    r"api/v2/dashboard/infoboxes",
    IndicatorFieldBoxInfoViewSet,
    basename="dashboard-infoboxes",
)
router.register(
    r"api/v2/dashboard/site-configs",
    SiteConfigurationViewSet,
    basename="dashboard-site-configs",
)

urlpatterns = []
