# sigic_idegeo/apps/idegeo_content_handler.py
from django.apps import AppConfig


class IdegeoContentHandlerConfig(AppConfig):
    name = "idegeo.content_handler"  # módulo real
    label = "idegeo_content_handler"  # nombre interno único
