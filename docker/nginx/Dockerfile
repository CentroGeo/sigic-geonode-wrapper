ARG BASE_IMAGE_VERSION
FROM geonode/nginx:${BASE_IMAGE_VERSION}

WORKDIR /etc/nginx/

COPY geonode.conf.envsubst ./sites-enabled/
