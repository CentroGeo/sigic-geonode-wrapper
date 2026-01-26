# sigic_idegeo/apps/idegeo_dashboard.py
from django.apps import AppConfig


class IdegeoDashboardConfig(AppConfig):
    name = "idegeo.dashboard"  # módulo real
    label = "idegeo_dashboard"  # nombre interno único
