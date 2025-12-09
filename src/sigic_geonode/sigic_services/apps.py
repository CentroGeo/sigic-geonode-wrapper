from django.apps import AppConfig


class SigicServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_services"
    verbose_name = "SIGIC Services"

    def ready(self):
        from .patches import (
            apply_service_model_patch,
            patch_service_serializer_validation,
        )

        apply_service_model_patch()
        patch_service_serializer_validation()
