from django.apps import AppConfig


class SigicServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_services"
    verbose_name = "SIGIC Services"

    def ready(self):
        # Import inside ready so Django is fully initialized before patching
        from .patches import (
            apply_owner_scoped_service_registration,
        )

        apply_owner_scoped_service_registration()