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

import logging

log = logging.getLogger("geonode")
_PATCHED = False
_PATCHED_AUTH_HEADER = False
_PATCHED_PROXY = False


def patch_placeholder():
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    # from geonode.services.serviceprocessors.wms import WmsServiceHandler

    def _empty_fun(self):
        return None

    return _empty_fun()
