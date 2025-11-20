# ==============================================================================
#  SIGIC – Sistema Integral de Gestión e Información Científica
#
#  Autor: César Benjamín (cesarbenjamin.net)
#  Derechos patrimoniales: CentroGeo (2025)
#
#  Nota:
#    Este código fue desarrollado para el proyecto SIGIC de
#    CentroGeo. Se mantiene crédito de autoría, pero la titularidad del código
#    pertenece a CentroGeo conforme a obra por encargo.
#
#  SPDX-License-Identifier: LicenseRef-SIGIC-CentroGeo
# ==============================================================================

# src/sigic_geonode/sigic_auth/urls.py

from django.urls import path

from sigic_geonode.router import router

from .views import (
    AssignRolesToUserView,
    MyGroupRolesView,
    RemoveRoleFromUserView,
    SigicGroupViewSet,
    SigicRoleViewSet,
    UserGroupRoleByUserViewSet,
    UserGroupRolesByEmailView,
    UserGroupRoleViewSet,
    UserInvitationAcceptView,
    UserInvitationCallbackView,
    UserInvitationCreateView,
)

router.register(r"api/v2/auth/groups", SigicGroupViewSet, basename="sigic-groups")
router.register(r"api/v2/auth/roles", SigicRoleViewSet, basename="sigic-roles")
router.register(
    r"api/v2/auth/user-group-roles",
    UserGroupRoleViewSet,
    basename="sigic-user-group-roles",
)
router.register(
    r"api/v2/auth/user",
    UserGroupRoleByUserViewSet,
    basename="sigic-user-group-roles-by-user",
)

urlpatterns = [
    path("api/v2/auth/group-roles/", MyGroupRolesView.as_view(), name="my-group-roles"),
    path(
        "api/v2/auth/user/<str:email>/group-roles/",
        UserGroupRolesByEmailView.as_view(),
        name="user-group-roles-by-email",
    ),
    path(
        "api/v2/auth/user/invitation",
        UserInvitationCreateView.as_view(),
        name="invitation-create",
    ),
    path(
        "api/v2/auth/user/invitation/accept/<str:token>/",
        UserInvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
    path(
        "api/v2/auth/user/invitation/callback/",
        UserInvitationCallbackView.as_view(),
        name="invitation-callback",
    ),
    path("groups/<int:group_id>/assign-role/", AssignRolesToUserView.as_view()),
    path("groups/<int:group_id>/remove-role/", RemoveRoleFromUserView.as_view()),
]
