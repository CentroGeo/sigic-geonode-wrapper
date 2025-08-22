ARG GEOSERVER_BASE_IMAGE_VERSION=2.24.4-v2
FROM geonode/geoserver:${GEOSERVER_BASE_IMAGE_VERSION}

RUN apt-get update && apt-get install -y gdal-bin && rm -rf /var/lib/apt/lists/*

COPY geoserver-2.24.2-geopkg-output-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-excel-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-ogr-wps-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-ogr-wfs-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/

COPY ogr2ogr.xml entrypoint.sh /usr/local/tomcat/tmp/

RUN chmod +x /usr/local/tomcat/tmp/entrypoint.sh && \
    chmod +x /usr/local/tomcat/tmp/multidump-alt.sh && \
    chmod +x /usr/local/tomcat/tmp/multidump.sh && \
    chmod +x /usr/local/tomcat/tmp/tasks.py






COMPOSE_PROJECT_NAME=sigic_geonode
# See httpss://github.com/containers/podman/issues/13889
# DOCKER_BUILDKIT=0
DOCKER_ENV=development
# See httpss://github.com/geosolutions-it/geonode-generic/issues/28
# to see why we force API version to 1.24
DOCKER_API_VERSION="1.24"
BACKUPS_VOLUME_DRIVER=local

GEONODE_BASE_IMAGE_VERSION=4.4.x
NGINX_BASE_IMAGE_VERSION=1.25.3-latest
LETSENCRYPT_BASE_IMAGE_VERSION=2.6.0-latest
GEOSERVER_BASE_IMAGE_VERSION=2.24.4-v2
GEOSERVER_DATA_BASE_IMAGE_VERSION=2.24.4-v3
POSTGRES_BASE_IMAGE_VERSION=15.3-latest

C_FORCE_ROOT=1
FORCE_REINIT=false
INVOKE_LOG_STDOUT=true

# LANGUAGE_CODE=it-it
# LANGUAGES=(('en-us','English'),('it-it','Italiano'))

DJANGO_SETTINGS_MODULE=sigic_geonode.settings
GEONODE_INSTANCE_NAME=geonode

# #################
# backend
# #################
POSTGRES_USER=postgres
POSTGRES_PASSWORD=5tYMd9845Mm3jZMWA78wTSd
GEONODE_DATABASE=geonodedevjun1
GEONODE_DATABASE_USER=geonode
GEONODE_DATABASE_PASSWORD=169vrQ79tdCm
GEONODE_GEODATABASE=geonodedevjun1_data
GEONODE_GEODATABASE_USER=geonode
GEONODE_GEODATABASE_PASSWORD=169vrQ79tdCm
GEONODE_DATABASE_SCHEMA=public
GEONODE_GEODATABASE_SCHEMA=public
DATABASE_HOST=10.2.102.215
DATABASE_PORT=5432
DATABASE_URL=postgis://geonode:169vrQ79tdCm@10.2.102.215:5432/geonodedevjun1
GEODATABASE_URL=postgis://geonode:169vrQ79tdCm@10.2.102.215:5432/geonodedevjun1_data
GEONODE_DB_CONN_MAX_AGE=0
GEONODE_DB_CONN_TOUT=5
DEFAULT_BACKEND_DATASTORE=datastore
BROKER_URL=amqp://guest:guest@rabbitmq:5672/
CELERY_BEAT_SCHEDULER=celery.beat:PersistentScheduler
ASYNC_SIGNALS=True

SITEURL=https://geonode.dev.geoint.mx/

ALLOWED_HOSTS=['django', 'geonode.dev.geoint.mx']

# Data Uploader
DEFAULT_BACKEND_UPLOADER=geonode.importer
TIME_ENABLED=True
MOSAIC_ENABLED=False

# #################
# nginx
# HTTPD Server
# #################
GEONODE_LB_HOST_IP=django
GEONODE_LB_PORT=8000
NGINX_BASE_URL=https://geonode.dev.geoint.mx

# IP or domain name and port where the server can be reached on HTTPS (leave HOST empty if you want to use HTTP only)
# port where the server can be reached on HTTPS
HTTP_HOST=geonode.dev.geoint.mx
HTTPS_HOST=

HTTP_PORT=80
HTTPS_PORT=443

# Let's Encrypt certificates for httpss encryption. You must have a domain name as HTTPS_HOST (doesn't work
# with an ip) and it must be reachable from the outside. This can be one of the following :
# disabled : we do not get a certificate at all (a placeholder certificate will be used)
# staging : we get staging certificates (are invalid, but allow to test the process completely and have much higher limit rates)
# production : we get a normal certificate (default)
LETSENCRYPT_MODE=disabled
# LETSENCRYPT_MODE=staging
# LETSENCRYPT_MODE=production

RESOLVER=127.0.0.11

# #################
# geoserver
# #################
GEOSERVER_LB_HOST_IP=geoserver
GEOSERVER_LB_PORT=8080
GEOSERVER_WEB_UI_LOCATION=https://geonode.dev.geoint.mx/geoserver/
GEOSERVER_PUBLIC_LOCATION=https://geonode.dev.geoint.mx/geoserver/
GEOSERVER_LOCATION=http://geoserver:8080/geoserver/
GEOSERVER_ADMIN_USER=admin
GEOSERVER_ADMIN_PASSWORD=zORCFqQQb2inh0D

OGC_REQUEST_TIMEOUT=30
OGC_REQUEST_MAX_RETRIES=1
OGC_REQUEST_BACKOFF_FACTOR=0.3
OGC_REQUEST_POOL_MAXSIZE=10
OGC_REQUEST_POOL_CONNECTIONS=10

# Java Options & Memory
ENABLE_JSONP=true
outFormat=text/javascript
GEOSERVER_JAVA_OPTS=-Djava.awt.headless=true -Xms4G -Xmx4G -Dgwc.context.suffix=gwc -XX:+UnlockDiagnosticVMOptions -XX:+LogVMOutput -XX:LogFile=/var/log/jvm.log -XX:PerfDataSamplingInterval=500 -XX:SoftRefLRUPolicyMSPerMB=36000 -XX:-UseGCOverheadLimit -XX:ParallelGCThreads=4 -Dfile.encoding=UTF8 -Djavax.servlet.request.encoding=UTF-8 -Djavax.servlet.response.encoding=UTF-8 -Duser.timezone=GMT -Dorg.geotools.shapefile.datetime=false -DGS-SHAPEFILE-CHARSET=UTF-8 -DGEOSERVER_CSRF_DISABLED=true -DPRINT_BASE_URL=https://geonode.dev.geoint.mx/geoserver/pdf -DALLOW_ENV_PARAMETRIZATION=true -Xbootclasspath/a:/usr/local/tomcat/webapps/geoserver/WEB-INF/lib/marlin-0.9.3-Unsafe.jar -Dsun.java2d.renderer=org.marlin.pisces.MarlinRenderingEngine

# #################
# Security
# #################
# Admin Settings
#
# ADMIN_PASSWORD is used to overwrite the GeoNode admin password **ONLY** the first time
# GeoNode is run. If you need to overwrite it again, you need to set the env var FORCE_REINIT,
# otherwise the invoke updateadmin task will be skipped and the current password already stored
# in DB will honored.

ADMIN_USERNAME=admin
ADMIN_PASSWORD=kiw0sdlgsxMeg5d
ADMIN_EMAIL=psp.cgarcia@centrogeo.edu.mx

# EMAIL Notifications
EMAIL_ENABLE=True
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=c2770541.ferozo.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=noreply@geoint.mx
DJANGO_EMAIL_HOST_PASSWORD=hcq@WA8S
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL='sigic@centrogeo.edu.mx'

# Session/Access Control
LOCKDOWN_GEONODE=False
X_FRAME_OPTIONS="SAMEORIGIN"
SESSION_EXPIRED_CONTROL_ENABLED=True
DEFAULT_ANONYMOUS_VIEW_PERMISSION=True
DEFAULT_ANONYMOUS_DOWNLOAD_PERMISSION=True

CORS_ALLOW_ALL_ORIGINS=True
GEOSERVER_CORS_ENABLED=True
GEOSERVER_CORS_ALLOWED_ORIGINS=*
GEOSERVER_CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,HEAD,OPTIONS
GEOSERVER_CORS_ALLOWED_HEADERS=*

# Users Registration
ACCOUNT_OPEN_SIGNUP=True
ACCOUNT_EMAIL_REQUIRED=True
ACCOUNT_APPROVAL_REQUIRED=True
ACCOUNT_CONFIRM_EMAIL_ON_GET=False
ACCOUNT_EMAIL_VERIFICATION=none
ACCOUNT_EMAIL_CONFIRMATION_EMAIL=False
ACCOUNT_EMAIL_CONFIRMATION_REQUIRED=False
ACCOUNT_AUTHENTICATION_METHOD=username_email
AUTO_ASSIGN_REGISTERED_MEMBERS_TO_REGISTERED_MEMBERS_GROUP_NAME=True

# OAuth2
OAUTH2_API_KEY=
OAUTH2_CLIENT_ID=05iIuYHFJX7Bfw4
OAUTH2_CLIENT_SECRET=XZwma3mvW9inJ27

# GeoNode APIs
API_LOCKDOWN=False
TASTYPIE_APIKEY=

# #################
# Production and
# Monitoring
# #################
DEBUG=True

SECRET_KEY='y-%x?a=?Y.5d&hMZi[or+stqh6>6f}WP\rMtDl]x.X=f(ZBtv^'

STATIC_ROOT=/mnt/volumes/statics/static/
MEDIA_ROOT=/mnt/volumes/statics/uploaded/
GEOIP_PATH=/mnt/volumes/statics/geoip.db

CACHE_BUSTING_STATIC_ENABLED=False

MEMCACHED_ENABLED=False
MEMCACHED_BACKEND=django.core.cache.backends.memcached.MemcachedCache
MEMCACHED_LOCATION=memcached:11211
MEMCACHED_LOCK_EXPIRE=3600
MEMCACHED_LOCK_TIMEOUT=10
#
# Options for memcached binary, e.g. -vvv to log all requests and cache hits
#
MEMCACHED_OPTIONS=

MAX_DOCUMENT_SIZE=200
CLIENT_RESULTS_LIMIT=5
API_LIMIT_PER_PAGE=1000

# GIS Client
GEONODE_CLIENT_LAYER_PREVIEW_LIBRARY=mapstore
MAPBOX_ACCESS_TOKEN=
BING_API_KEY=
GOOGLE_API_KEY=

# Monitoring
MONITORING_ENABLED=False
MONITORING_DATA_TTL=365
USER_ANALYTICS_ENABLED=True
USER_ANALYTICS_GZIP=True
CENTRALIZED_DASHBOARD_ENABLED=False
MONITORING_SERVICE_NAME=local-geonode
MONITORING_HOST_NAME=geonode

# Other Options/Contribs
MODIFY_TOPICCATEGORY=True
AVATAR_GRAVATAR_SSL=True
EXIF_ENABLED=True
CREATE_LAYER=True
FAVORITE_ENABLED=True

# Advanced Workflow
RESOURCE_PUBLISHING=False
ADMIN_MODERATE_UPLOADS=True

# PostgreSQL
POSTGRESQL_MAX_CONNECTIONS=200

# Common containers restart policy
RESTART_POLICY_CONDITION="on-failure"
RESTART_POLICY_DELAY="5s"
RESTART_POLICY_MAX_ATTEMPTS="3"
RESTART_POLICY_WINDOW=120s

DEFAULT_MAX_UPLOAD_SIZE=5368709120
DEFAULT_MAX_PARALLEL_UPLOADS_PER_USER=5

SOCIALACCOUNT_OIDC_PROVIDER_ENABLED=True
SOCIALACCOUNT_ADAPTER=sigic_geonode.sigic_auth.account_adapters.SigicOpenIDConnectAdapter
SOCIALACCOUNT_PROVIDER_NAME=SIGICAuth

SOCIALACCOUNT_OIDC_ACCESS_TOKEN_URL=https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/token
SOCIALACCOUNT_OIDC_AUTHORIZE_URL=https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/auth
SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER=https://iam.dev.geoint.mx/realms/sigic
SOCIALACCOUNT_OIDC_PROFILE_URL=https://iam.dev.geoint.mx/realms/sigic/protocol/openid-connect/userinfo
