from geonode.people.adapters import LocalAccountAdapter, GenericOpenIDConnectAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from allauth.account.utils import user_username
from django.utils.text import slugify
import logging

logger = logging.getLogger(__name__)


class SigicLocalAccountAdapter(LocalAccountAdapter):
    def populate_username(self, request, user):
        """Set username from social account's preferred_username if available"""
        sociallogin = getattr(user, 'socialaccount_set', None)
        if sociallogin:
            try:
                # Get first related socialaccount (should only be one for OIDC)
                account = user.socialaccount_set.first()
                preferred_username = account.extra_data.get("preferred_username")
                if preferred_username:
                    user_username(user, preferred_username)
                    return
            except Exception:
                pass  # fallback to default behavior below

        # Fallback if not coming from OIDC or preferred_username missing
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
        logger.warning("🚨 preferred_username del token: %s", preferred_username)
        logger.warning("👤 Antes del cambio - login.user.username: %s", login.user.username)

        if preferred_username:
            login.user.username = preferred_username
            login.account.user = login.user  # <- importante

        logger.warning("✅ Después del cambio - login.user.username: %s", login.user.username)

        return login



