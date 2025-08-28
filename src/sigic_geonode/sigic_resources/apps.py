import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MonkeyPatchResourcesConfig(AppConfig):
    name = "sigic_geonode.sigic_resources"
    verbose_name = "Monkey Patch Resources"

    def ready(self):
        try:
            # Importa y ejecuta el parche al iniciar Django
            import sigic_geonode.sigic_resources.patches  # Import for side effects: applies monkey patches on app startup. Do not remove. # noqa: F401

            logger.info("Monkey patch importado correctamente")
        except Exception:
            logger.exception("Falló el monkey patch")
