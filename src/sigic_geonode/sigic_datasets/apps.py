import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MonkeyPatchDatasetsConfig(AppConfig):
    name = "sigic_geonode.sigic_datasets"
    verbose_name = "Monkey Patch Datasets"

    def ready(self):
        try:
            # Importa y ejecuta el parche al iniciar Django
            import sigic_geonode.sigic_datasets.patches  # noqa: F401 importar para causar side effects: No quitar.

            logger.info("Monkey patch importado correctamente")
        except Exception:
            logger.exception("Falló el monkey patch")
