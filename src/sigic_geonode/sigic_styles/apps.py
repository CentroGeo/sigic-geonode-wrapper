from django.apps import AppConfig


class SigicStylesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_styles"
    verbose_name = "SIGIC Styles Manager"

    def ready(self):
        print(">>> SIGIC Styles ready() ejecutado")
        import geonode.layers.api.views as layers_api_views
        from .views import SigicDatasetViewSet
        layers_api_views.DatasetViewSet = SigicDatasetViewSet
        print(">>> DatasetViewSet parcheado por SIGIC Styles")
