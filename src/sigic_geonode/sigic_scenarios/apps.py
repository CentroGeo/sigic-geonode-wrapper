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

from django.apps import AppConfig


class SigicScenariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_scenarios"
    verbose_name = "SIGIC Escenarios"
