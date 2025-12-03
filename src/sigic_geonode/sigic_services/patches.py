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

# sigic_services/patches.py

import logging

from geonode.harvesting.harvesters.wms import WMSServiceHarvester

logger = logging.getLogger(__name__)

_original_run = WMSServiceHarvester.run


def patched_run(self, exec_request, *args, **kwargs):
    """
    Intercepta el run del WMS Harvester y
    ajusta dinámicamente el default_owner
    al usuario que lanzó la importación.
    """

    if exec_request and hasattr(exec_request, "user") and exec_request.user:
        logger.info(
            f"[SIGIC PATCH] Setting harvester default_owner "
            f"from {getattr(self, 'default_owner', None)} "
            f"to {exec_request.user}"
        )
        self.default_owner = exec_request.user

    return _original_run(self, exec_request, *args, **kwargs)


# Aplicar el monkeypatch
WMSServiceHarvester.run = patched_run
