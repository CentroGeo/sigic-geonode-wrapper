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

import logging

from allauth.account.utils import user_username
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import ValidationError
from geonode.people.adapters import GenericOpenIDConnectAdapter, LocalAccountAdapter

logger = logging.getLogger(__name__)


class SigicSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        extra = sociallogin.account.extra_data

        user.username = extra.get("email", "")
        user.email = extra.get("email", "")
        user.first_name = extra.get("given_name", "")
        user.last_name = extra.get("family_name", "")

        return user


class SigicLocalAccountAdapter(LocalAccountAdapter):
    def populate_username(self, request, user):
        """Set username from social account's preferred_username if available"""
        sociallogin = getattr(user, "socialaccount_set", None)
        if sociallogin:
            try:
                account = user.socialaccount_set.first()
                preferred_username = account.extra_data.get("preferred_username")
                if preferred_username:
                    user_username(user, preferred_username)
                    return
            except Exception as e:
                logger.error("Error al recuperar preferred_username: %s", e)
        try:
            user.full_clean()
            safe_username = user_username(user)
        except ValidationError:
            safe_username = self.generate_unique_username(
                [
                    user.first_name,
                    user.last_name,
                    user.email,
                ]
            )
        user_username(user, safe_username)


class SigicOpenIDConnectAdapter(GenericOpenIDConnectAdapter):
    def complete_login(self, request, app, token, response, **kwargs):
        login = super().complete_login(request, app, token, response, **kwargs)

        extra = login.account.extra_data or {}
        print("Extra data from OIDC response:", extra)
        user = login.user

        # --- FORZAR PERFIL (equivalente a populate_user) ---
        email = extra.get("email")
        username = email
        first_name = extra.get("given_name")
        last_name = extra.get("family_name")

        if username:
            user.username = username

        if email:
            user.email = email

        if first_name:
            user.first_name = first_name

        if last_name:
            user.last_name = last_name

        login.account.user = user
        return login
