from django.urls import path

from .views import MeAvatarView, MeProfileView

urlpatterns = [
    path(
        "api/v2/account/me/profile/",
        MeProfileView.as_view(),
        name="me-profile",
    ),
    path("api/v2/account/me/avatar/", MeAvatarView.as_view(), name="me-avatar"),
]
