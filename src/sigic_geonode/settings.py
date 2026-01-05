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
# flake8: noqa evitar errores por imports estrellas y variables no declaradas

import ast

# Django settings for the GeoNode project.
import os

try:
    from urllib.parse import urlparse, urlunparse
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen
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

# Apps que deben cargarse ANTES (para monkeypatches)
INSTALLED_APPS = (
    "sigic_geonode.sigic_styles",  # ✔ SE EJECUTA ANTES QUE geonode.layers
) + INSTALLED_APPS

# Apps que no necesitan ejecutarse antes
INSTALLED_APPS += (
    "sigic_geonode.sigic_auth",
    "sigic_geonode.sigic_datasets",
    "sigic_geonode.sigic_resources",
    "sigic_geonode.sigic_ia_media_uploads",
    "sigic_geonode.sigic_requests",
    "sigic_geonode.sigic_account",
)

MIDDLEWARE = [
    "sigic_geonode.sigic_auth.middleware.SkipCSRFMiddlewareForJWT"
    if mw == "django.middleware.csrf.CsrfViewMiddleware"
    else mw
    for mw in MIDDLEWARE
]

MIDDLEWARE += [
    "sigic_geonode.sigic_auth.middleware.KeycloakUserFromBearerInjectionMiddleware",
]

SOCIALACCOUNT_OIDC_PROVIDER_ENABLED = ast.literal_eval(
    os.environ.get("SOCIALACCOUNT_OIDC_PROVIDER_ENABLED", "True")
)
SOCIALACCOUNT_OIDC_PROVIDER = os.getenv(
    "SOCIALACCOUNT_OIDC_PROVIDER", "geonode_openid_connect"
)
SOCIALACCOUNT_ADAPTER = os.environ.get(
    "SOCIALACCOUNT_ADAPTER",
    "sigic_geonode.sigic_auth.account_adapters.SigicSocialAccountAdapter",
)
SOCIALACCOUNT_PROVIDER_NAME = os.getenv("SOCIALACCOUNT_PROVIDER_NAME", "SIGICAuth")

SOCIALACCOUNT_PROVIDERS = {
    SOCIALACCOUNT_OIDC_PROVIDER: {
        "NAME": SOCIALACCOUNT_OIDC_PROVIDER,
        "SCOPE": ["openid", "email", "profile"],
        "AUTH_PARAMS": {},
        "COMMON_FIELDS": {
            "email": "email",
            "last_name": "family_name",
            "first_name": "given_name",
        },
        "USER_FIELDS": {"username": "preferred_username"},
        "ACCESS_TOKEN_URL": os.getenv(
            "SOCIALACCOUNT_OIDC_ACCESS_TOKEN_URL",
            "https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/token",
        ),
        "AUTHORIZE_URL": os.getenv(
            "SOCIALACCOUNT_OIDC_AUTHORIZE_URL",
            "https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/auth",
        ),
        "ID_TOKEN_ISSUER": os.getenv(
            "SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER",
            "https://iam.dev.geoint.mx/realms/sigic",
        ),
        "PROFILE_URL": os.getenv(
            "SOCIALACCOUNT_OIDC_PROFILE_URL",
            "https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/userinfo",
        ),
        "OAUTH_PKCE_ENABLED": ast.literal_eval(
            os.getenv("SOCIALACCOUNT_OIDC_OAUTH_PKCE_ENABLED", "True")
        ),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "sigic_geonode.sigic_auth.keycloak.KeycloakJWTAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "dynamic_rest.renderers.DynamicBrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "geonode.base.api.exceptions.geonode_exception_handler",
}

HARVESTER_TYPES = {
    "FILE": "sigic_geonode.sigic_remote_services.file_harvester.FileHarvester",
}

SERVICES_TYPE_MODULES = [
    "sigic_geonode.sigic_remote_services.file_service.FileServiceInfo",
]

CELERY_TASK_QUEUES += (
    Queue(
        "sigic_geonode.sync_geoserver",
        GEONODE_EXCHANGE,
        routing_key="sigic_geonode.sync_geoserver",
    ),
)
# Valor predeterminado si no existe la variable de entorno
DEFAULT_ALLOWED_DOCUMENT_TYPES = (
    "txt",
    "csv",
    "log",
    "doc",
    "docx",
    "ods",
    "odt",
    "sld",
    "qml",
    "xls",
    "xlsx",
    "xml",
    "bm",
    "bmp",
    "dwg",
    "dxf",
    "fif",
    "gif",
    "jpg",
    "jpe",
    "jpeg",
    "png",
    "tif",
    "tiff",
    "pbm",
    "odp",
    "ppt",
    "pptx",
    "pdf",
    "tar",
    "tgz",
    "rar",
    "gz",
    "7z",
    "zip",
    "aif",
    "aifc",
    "aiff",
    "au",
    "mp3",
    "mpga",
    "wav",
    "afl",
    "avi",
    "avs",
    "fli",
    "mp2",
    "mp4",
    "mpg",
    "ogg",
    "webm",
    "3gp",
    "flv",
    "vdo",
    "glb",
    "pcd",
    "gltf",
    "ifc",
    "json",
)

# Leer la variable de entorno y dividirla por comas
env_allowed_types = os.getenv("ALLOWED_DOCUMENT_TYPES")
if env_allowed_types:
    ALLOWED_DOCUMENT_TYPES = [
        ext.strip()
        for ext in env_allowed_types.replace(" ", "").split(",")
        if ext.strip()
    ]
else:
    ALLOWED_DOCUMENT_TYPES = list(DEFAULT_ALLOWED_DOCUMENT_TYPES)

DEFAULT_HOME_PATH = os.getenv("DEFAULT_HOME_PATH", "")
