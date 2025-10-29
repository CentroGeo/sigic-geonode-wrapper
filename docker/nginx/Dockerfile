# ARG BASE_IMAGE_VERSION
# FROM geonode/nginx:${BASE_IMAGE_VERSION}
FROM openresty/openresty:1.25.3.1-2-alpine

RUN apk add --no-cache bash gettext curl inotify-tools

COPY nginx.conf.envsubst nginx.https.available.conf.envsubst /etc/nginx/
COPY geonode.conf.envsubst /etc/nginx/sites-enabled/

COPY docker-autoreload.sh docker-entrypoint.sh /

RUN chmod +x /docker-autoreload.sh
RUN chmod +x /docker-entrypoint.sh

RUN bash -c '\
  if [ ! -d /etc/nginx/modules ]; then \
    if [ -d /usr/local/openresty/nginx/modules ]; then \
      ln -sf /usr/local/openresty/nginx/modules /etc/nginx/modules; \
    elif [ -d /usr/lib/nginx/modules ]; then \
      ln -sf /usr/lib/nginx/modules /etc/nginx/modules; \
    else \
      mkdir -p /etc/nginx/modules; \
    fi; \
  fi'

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
