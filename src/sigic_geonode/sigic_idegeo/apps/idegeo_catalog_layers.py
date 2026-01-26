# sigic_idegeo/apps/idegeo_catalog_layers.py
from django.apps import AppConfig


class IdegeoCatalogLayersConfig(AppConfig):
    name = "idegeo.catalog.layers"  # módulo real
    label = "idegeo_catalog_layers"  # nombre interno único
