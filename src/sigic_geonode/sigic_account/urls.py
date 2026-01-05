from django.urls import path

from .views import MeProfileView

urlpatterns = [
    path(
        "api/v2/account/me/profile/",
        MeProfileView.as_view(),
        name="me-profile",
    ),
]
