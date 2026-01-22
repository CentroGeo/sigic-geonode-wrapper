FROM geonode/geonode-base:latest-ubuntu-22.04
LABEL \
  org.opencontainers.image.title="sigic-geonode-wrapper" \
  org.opencontainers.image.version="${WRAPPER_VERSION}" \
  org.opencontainers.image.description="SIGIC GeoNode wrapper" \
  sigic.wrapper.version="${WRAPPER_VERSION}" \
  sigic.geonode.version="${GEONODE_VERSION}" \
  sigic.patch="${SIGIC_PATCH}"

ARG REQUIREMENTS_VARIANT=bundle
ARG USE_IDEGEOWEB=false

ENV USE_IDEGEOWEB=${USE_IDEGEOWEB}

RUN mkdir -p /usr/src/sigic_geonode
RUN apt-get update -y && apt-get install curl wget unzip gnupg2 locales build-essential -y
RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

COPY src /usr/src/sigic_geonode/
WORKDIR /usr/src/sigic_geonode

COPY src/wait-for-databases.sh /usr/bin/wait-for-databases
RUN chmod +x /usr/bin/wait-for-databases
RUN chmod +x /usr/src/sigic_geonode/tasks.py
RUN chmod +x /usr/src/sigic_geonode/entrypoint.sh

COPY src/celery.sh /usr/bin/celery-commands
RUN chmod +x /usr/bin/celery-commands

COPY src/celery-cmd /usr/bin/celery-cmd
RUN chmod +x /usr/bin/celery-cmd

COPY vendor/idegeo/geoweb-0.1.0-py3-none-any.whl /tmp/

RUN yes w | pip install --src /usr/src -r requirements/${REQUIREMENTS_VARIANT}.txt && \
    yes w | pip install -e .



RUN if [ "$USE_IDEGEOWEB" = "true" ] || [ "$USE_IDEGEOWEB" = "True" ]; then \
        apt-get update && \
        apt-get install -y --no-install-recommends \
            python3-dev \
            libpq-dev \
            libcairo2 \
            libpango-1.0-0 \
            libpangocairo-1.0-0 \
            libpangoft2-1.0-0 \
            libharfbuzz0b \
            libharfbuzz-subset0 \
            libfontconfig1 \
            libgdk-pixbuf2.0-0 \
            libglib2.0-0 \
            fonts-dejavu \
            fonts-droid-fallback \
            fonts-freefont-ttf \
            fonts-liberation \
        && rm -rf /var/lib/apt/lists/* ; \
        pip install /tmp/geoweb-0.1.0-py3-none-any.whl ; \
    fi



# Cleanup apt update lists
RUN apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Export ports
EXPOSE 8000

# We provide no command or entrypoint as this image can be used to serve the django project or run celery tasks
# ENTRYPOINT /usr/src/sigic_geonode/entrypoint.sh
