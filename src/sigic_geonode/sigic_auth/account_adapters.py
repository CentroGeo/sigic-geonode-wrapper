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

        # Aquí sí tienes acceso directo al "email"
        email = data.get("email")
        preferred_username = data.get("preferred_username")

        if email:
            user.email = email
        if preferred_username:
            user.username = preferred_username
        else:
            user.username = email
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
        preferred_username = login.account.extra_data.get("preferred_username")
        email = login.account.extra_data.get("email")

        if preferred_username:
            login.user.username = preferred_username
        if email:
            login.user.email = email

        login.account.user = login.user
        return login

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        # Aseguramos persistencia explícita del email
        extra = sociallogin.account.extra_data
        if extra.get("email") and user.email != extra["email"]:
            user.email = extra["email"]
            user.save(update_fields=["email"])
        return user
