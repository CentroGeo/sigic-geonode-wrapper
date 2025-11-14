from django.apps import AppConfig


class SigicStylesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_styles"
    verbose_name = "SIGIC Styles Manager"

    def ready(self):
        # unregister after all apps loaded
        try:
            admin.site.unregister(Dataset)
        except NotRegistered:
            pass

        try:
            admin.site.unregister(Style)
        except NotRegistered:
            pass