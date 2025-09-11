from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class UploadsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "sigic_geonode.sigic_ia_media_uploads"
    verbose_name = "Media Uploads"

    def ready(self):
        try:
            logger.info("La app 'uploads' está lista")
            # Aquí podrías poner inicializaciones, signals, etc.
        except Exception:
            logger.exception("Error al iniciar la app 'uploads'")
