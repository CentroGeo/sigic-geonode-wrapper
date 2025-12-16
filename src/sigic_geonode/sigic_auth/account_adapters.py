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
from allauth.account.utils import user_username, user_email

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
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)

        extra = sociallogin.account.extra_data

        preferred_username = extra.get("preferred_username")
        email = extra.get("email")

        updated = False

        if preferred_username and user.username != preferred_username:
            # 👈 CLAVE: usar helper de allauth, no asignación directa
            user_username(user, preferred_username)
            updated = True

        if email and user.email != email:
            user_email(user, email)
            updated = True

        if updated:
            user.save(update_fields=["username", "email"])

        return user
