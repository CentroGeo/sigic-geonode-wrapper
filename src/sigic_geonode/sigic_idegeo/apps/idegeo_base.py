# sigic_idegeo/apps/idegeo_base.py
from django.apps import AppConfig


class IdegeoBaseConfig(AppConfig):
    name = "idegeo.base"  # módulo real
    label = "idegeo_base"  # nombre interno único
