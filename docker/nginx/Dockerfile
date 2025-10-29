# ARG BASE_IMAGE_VERSION
# FROM geonode/nginx:${BASE_IMAGE_VERSION}
FROM openresty/openresty:1.25.3.1-2-alpine

RUN apk add --no-cache bash gettext

COPY nginx.conf.envsubst nginx.https.available.conf.envsubst /etc/nginx/
COPY geonode.conf.envsubst /etc/nginx/sites-enabled/

COPY docker-autoreload.sh docker-entrypoint.sh /

RUN chmod +x /docker-autoreload.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
