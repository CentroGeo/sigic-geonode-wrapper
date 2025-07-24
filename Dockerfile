FROM geonode/geonode-base:latest-ubuntu-22.04
LABEL GeoNode development team

RUN mkdir -p /usr/src/sigic_geonode

RUN apt-get update -y && apt-get install curl wget unzip gnupg2 locales -y

RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen \

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

RUN yes w | pip install --src /usr/src -r requirements.txt && \
    yes w | pip install -e .

# Cleanup apt update lists
RUN apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Export ports
EXPOSE 8000

# We provide no command or entrypoint as this image can be used to serve the django project or run celery tasks
# ENTRYPOINT /usr/src/sigic_geonode/entrypoint.sh
