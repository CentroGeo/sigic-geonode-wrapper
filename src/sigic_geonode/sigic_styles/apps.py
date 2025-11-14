from django.apps import AppConfig
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from geonode.layers.models import Dataset, Style


class SigicStylesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_styles"
    verbose_name = "SIGIC Styles Manager"

    def ready(self):
        # Se ejecuta DESPUÉS de que GeoNode registró todo
        try:
            admin.site.unregister(Dataset)
        except NotRegistered:
            pass

        try:
            admin.site.unregister(Style)
        except NotRegistered:
            pass

        # Importar tu admin, ya limpio
        import sigic_geonode.sigic_styles.admin