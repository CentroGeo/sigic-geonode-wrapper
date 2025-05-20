from geonode.people.adapters import LocalAccountAdapter, GenericOpenIDConnectAdapter
from django.core.exceptions import ValidationError
from allauth.account.utils import user_username
import logging

logger = logging.getLogger(__name__)


class SigicLocalAccountAdapter(LocalAccountAdapter):
    def populate_username(self, request, user):
        """Set username from social account's preferred_username if available"""
        sociallogin = getattr(user, 'socialaccount_set', None)
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
            safe_username = self.generate_unique_username([
                user.first_name,
                user.last_name,
                user.email,
            ])
        user_username(user, safe_username)


class SigicOpenIDConnectAdapter(GenericOpenIDConnectAdapter):
    def complete_login(self, request, app, token, response, **kwargs):
        login = super().complete_login(request, app, token, response, **kwargs)
        preferred_username = login.account.extra_data.get("preferred_username")
        if preferred_username:
            login.user.username = preferred_username
            login.account.user = login.user
        return login
