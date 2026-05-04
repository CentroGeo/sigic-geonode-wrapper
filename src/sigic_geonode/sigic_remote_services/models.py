# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Derechos patrimoniales: CentroGeo (2025)
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# =============================================================================

from django.db import models


class RemoteLayerTypename(models.Model):
    """
    Almacena el typename real de una capa cosechada de un servicio remoto.

    El sistema de cosecha agrega el sufijo _h{harvester_id} al campo 'alternate'
    de cada Dataset para garantizar unicidad en la BD cuando múltiples usuarios
    cosechan el mismo servicio. Este modelo guarda el typename original sin sufijo,
    necesario para realizar peticiones WMS/WFS al servidor externo.
    """

    dataset = models.OneToOneField(
        "layers.Dataset",
        on_delete=models.CASCADE,
        related_name="remote_layer_typename",
        primary_key=True,
    )
    typename = models.CharField(max_length=512)

    class Meta:
        app_label = "sigic_remote_services"

    def __str__(self):
        return f"Dataset {self.dataset_id} → {self.typename}"
