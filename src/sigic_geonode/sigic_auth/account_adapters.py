import logging
import re
from allauth.account.utils import user_username
from django.core.exceptions import ValidationError
from geonode.people.adapters import GenericOpenIDConnectAdapter, LocalAccountAdapter

logger = logging.getLogger(__name__)
EMAIL_REGEX = re.compile(r".+@.+")


class SigicLocalAccountAdapter(LocalAccountAdapter):
    def populate_username(self, request, user):
        """Set username from social account's preferred_username if available"""
        sociallogin = getattr(user, "socialaccount_set", None)
        if sociallogin:
            try:
                account = user.socialaccount_set.first()

                preferred_username = account.extra_data.get("preferred_username")
                username_from_token = (
                    preferred_username
                    if preferred_username and EMAIL_REGEX.match(preferred_username)
                    else data.get("email") or data.get("username")
                )

                if username_from_token:
                    user_username(user, username_from_token)
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
        if not preferred_username or not re.match(r".+@.+", preferred_username):
            preferred_username = data.get("email") or data.get("username")
        login.user.username = preferred_username
        login.account.user = login.user
        return login
