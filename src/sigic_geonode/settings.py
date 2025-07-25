# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

# Django settings for the GeoNode project.
import os
import ast

try:
    from urllib.parse import urlparse, urlunparse
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request
    from urlparse import urlparse, urlunparse
# Load more settings from a file called local_settings.py if it exists
try:
    from sigic_geonode.local_settings import *
#    from geonode.local_settings import *
except ImportError:
    from geonode.settings import *

#
# General Django development settings
#
PROJECT_NAME = "sigic_geonode"

# add trailing slash to site url. geoserver url will be relative to this
if not SITEURL.endswith("/"):
    SITEURL = "{}/".format(SITEURL)

SITENAME = os.getenv("SITENAME", "sigic_geonode")

# Defines the directory that contains the settings file as the LOCAL_ROOT
# It is used for relative settings elsewhere.
LOCAL_ROOT = os.path.abspath(os.path.dirname(__file__))

WSGI_APPLICATION = "{}.wsgi.application".format(PROJECT_NAME)

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "en")

if PROJECT_NAME not in INSTALLED_APPS:
    INSTALLED_APPS = (PROJECT_NAME,) + INSTALLED_APPS

# Location of url mappings
ROOT_URLCONF = os.getenv("ROOT_URLCONF", "{}.urls".format(PROJECT_NAME))

# Additional directories which hold static files
# - Give priority to local geonode-project ones
STATICFILES_DIRS = [
    os.path.join(LOCAL_ROOT, "static"),
] + STATICFILES_DIRS

# Location of locale files
LOCALE_PATHS = (os.path.join(LOCAL_ROOT, "locale"),) + LOCALE_PATHS

TEMPLATES[0]["DIRS"].insert(0, os.path.join(LOCAL_ROOT, "templates"))
loaders = TEMPLATES[0]["OPTIONS"].get("loaders") or [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]
# loaders.insert(0, 'apptemplates.Loader')
TEMPLATES[0]["OPTIONS"]["loaders"] = loaders
TEMPLATES[0].pop("APP_DIRS", None)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d "
            "%(thread)d %(message)s"
        },
        "simple": {
            "format": "%(message)s",
        },
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
        },
        "geonode": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "geoserver-restconfig.catalog": {
            "handlers": ["console"],
            "level": "ERROR",
        },
        "owslib": {
            "handlers": ["console"],
            "level": "ERROR",
        },
        "pycsw": {
            "handlers": ["console"],
            "level": "ERROR",
        },
        "celery": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "mapstore2_adapter.plugins.serializers": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "geonode_logstash.logstash": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

CENTRALIZED_DASHBOARD_ENABLED = ast.literal_eval(
    os.getenv("CENTRALIZED_DASHBOARD_ENABLED", "False")
)
if (
    CENTRALIZED_DASHBOARD_ENABLED
    and USER_ANALYTICS_ENABLED
    and "geonode_logstash" not in INSTALLED_APPS
):
    INSTALLED_APPS += ("geonode_logstash",)

    CELERY_BEAT_SCHEDULE["dispatch_metrics"] = {
        "task": "geonode_logstash.tasks.dispatch_metrics",
        "schedule": 3600.0,
    }

LDAP_ENABLED = ast.literal_eval(os.getenv("LDAP_ENABLED", "False"))
if LDAP_ENABLED and "geonode_ldap" not in INSTALLED_APPS:
    INSTALLED_APPS += ("geonode_ldap",)

# Add your specific LDAP configuration after this comment:
# https://docs.geonode.org/en/master/advanced/contrib/#configuration

INSTALLED_APPS += (
    # "sigic_geonode.misc",  # esto de los links ya no va a ir dentro de geonode, debe ser un proyecto aparte
)

MIDDLEWARE = [
    'sigic_geonode.auth.middleware.SkipCSRFMiddlewareForJWT' if mw == 'django.middleware.csrf.CsrfViewMiddleware' else mw
    for mw in MIDDLEWARE
]

SOCIALACCOUNT_OIDC_PROVIDER_ENABLED = ast.literal_eval(os.environ.get("SOCIALACCOUNT_OIDC_PROVIDER_ENABLED", "True"))
SOCIALACCOUNT_OIDC_PROVIDER=os.getenv("SOCIALACCOUNT_OIDC_PROVIDER", "geonode_openid_connect")
SOCIALACCOUNT_ADAPTER = os.environ.get("SOCIALACCOUNT_ADAPTER", "sigic_geonode.auth.account_adapters.SigicOpenIDConnectAdapter")
SOCIALACCOUNT_PROVIDER_NAME=os.getenv("SOCIALACCOUNT_PROVIDER_NAME", "SIGICSSO")

SOCIALACCOUNT_PROVIDERS={
    SOCIALACCOUNT_OIDC_PROVIDER: {
        "NAME": SOCIALACCOUNT_OIDC_PROVIDER,
        "SCOPE": ["openid", "email", "profile"],
        "AUTH_PARAMS": {},
        "COMMON_FIELDS": {
            "email": "email",
            "last_name": "family_name",
            "first_name": "given_name"
        },
        "USER_FIELDS": {
            "username": "preferred_username"
        },
        "ACCESS_TOKEN_URL": os.getenv("SOCIALACCOUNT_OIDC_ACCESS_TOKEN_URL", "https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/token"),
        "AUTHORIZE_URL": os.getenv("SOCIALACCOUNT_OIDC_AUTHORIZE_URL", "https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/auth"),
        "ID_TOKEN_ISSUER": os.getenv("SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER", "https://iam.dev.geoint.mx/realms/sigic"),
        "PROFILE_URL": os.getenv("SOCIALACCOUNT_OIDC_PROFILE_URL", "https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/userinfo"),
        "OAUTH_PKCE_ENABLED": ast.literal_eval(os.getenv("SOCIALACCOUNT_OIDC_OAUTH_PKCE_ENABLED", "True"))
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "sigic_geonode.auth.keycloak.KeycloakJWTAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "dynamic_rest.renderers.DynamicBrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "geonode.base.api.exceptions.geonode_exception_handler",
}
