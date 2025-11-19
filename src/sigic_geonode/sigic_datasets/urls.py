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

from django.urls import path

from .views import DatasetKeywordsViewSet

urlpatterns = [
    path(
        "api/v2/datasets/<int:dataset_pk>/keywords/",
        DatasetKeywordsViewSet.as_view(
            {
                "get": "list",
                "post": "create",
                "put": "update",
                "delete": "destroy",
            }
        ),
        name="dataset-keywords",
    ),
]
