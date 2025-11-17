from django.apps import AppConfig


class SigicStylesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigic_geonode.sigic_styles"
    verbose_name = "SIGIC Styles Manager"

    def ready(self):
        # Debug de arranque
        print(">>> SIGIC Styles ready() ejecutado")

        # 1) Importamos el router de la API v2 (EL REAL)
        from geonode.api import urls as api_urls

        # 2) Importamos el viewset original… solo para imprimirlo
        from geonode.api.views import DatasetViewSet as GeoNodeDatasetViewSet

        print(">>> Antes parcheo (DatasetViewSet API v2):", GeoNodeDatasetViewSet)

        # 3) Importamos TU viewset
        from .views import SigicDatasetViewSet

        # 4) Quitamos el DatasetViewSet original del router
        api_urls.router.registry = [
            (prefix, viewset, basename)
            for (prefix, viewset, basename) in api_urls.router.registry
            if prefix != "datasets"
        ]

        # 5) Registramos el tuyo
        api_urls.router.register("datasets", SigicDatasetViewSet, basename="datasets")

        print(">>> Después parcheo (DatasetViewSet API v2):", SigicDatasetViewSet)
        print(">>> Router datasets quedó parchado correctamente.")

