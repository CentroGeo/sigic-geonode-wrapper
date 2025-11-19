ARG BASE_IMAGE_VERSION
FROM geonode/postgis:${BASE_IMAGE_VERSION}

COPY scripts /docker-entrypoint-initdb.d/

RUN apk add git build-base clang15 llvm15-dev
RUN git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make \
    && make install \
    && cd .. \
    && rm -rf pgvector
