from django.apps import AppConfig

# from django.conf import settings


class SigicServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_services"

    def ready(self):
        from .patches import patch_placeholder

        patch_placeholder()
