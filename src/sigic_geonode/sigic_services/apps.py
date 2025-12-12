from django.apps import AppConfig


class SigicServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_services"
    verbose_name = "SIGIC Services"

    def ready(self):
        from .patches import patch_service_model

        patch_service_model()
