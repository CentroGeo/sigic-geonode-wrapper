from django.apps import AppConfig


class SigicStylesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_styles"
    verbose_name = "SIGIC Styles Manager"

    def ready(self):
        from django.contrib import admin
        from django.contrib.admin.sites import NotRegistered
        from geonode.layers.models import Dataset, Style

        try:
            admin.site.unregister(Dataset)
        except NotRegistered:
            pass

        try:
            admin.site.unregister(Style)
        except NotRegistered:
            pass

        import sigic_geonode.sigic_styles.admin