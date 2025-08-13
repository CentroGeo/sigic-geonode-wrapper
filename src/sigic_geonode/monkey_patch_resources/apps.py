from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class MonkeyPatchResourcesConfig(AppConfig):
    name = "sigic_geonode.monkey_patch_resources"
    verbose_name = "Monkey Patch Resources"

    def ready(self):
        try:
            # Importa y ejecuta el parche al iniciar Django
            import sigic_geonode.monkey_patch_resources.monkey_patch
            logger.info("Monkey patch importado correctamente")
        except Exception:
            logger.exception("Falló el monkey patch")
