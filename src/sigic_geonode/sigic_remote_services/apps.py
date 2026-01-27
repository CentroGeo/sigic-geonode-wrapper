# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from django.apps import AppConfig


class SigicRemoteServicesConfig(AppConfig):
    name = "sigic_geonode.sigic_remote_services"
    verbose_name = "SIGIC Remote Services"

    def ready(self):
        # Importar patches para aplicarlos al cargar la app
        from . import patches  # noqa: F401
