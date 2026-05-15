# ==============================================================================
#  SIGIC - Sistema Integral de Gestion e Informacion Cientifica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from django.urls import path

from sigic_geonode.router import router

from .views import CategoriesView, DataImporterViewSet

router.register(r"api/v2/data-importer/jobs", DataImporterViewSet, basename="data-importer")

urlpatterns = [
    path("api/v2/data-importer/categories/", CategoriesView.as_view(), name="data-importer-categories"),
]
