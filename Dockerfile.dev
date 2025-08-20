FROM geonode/geonode-base:latest-ubuntu-22.04
LABEL GeoNode development team

RUN mkdir -p /usr/src/sigic_geonode
WORKDIR /usr/src/sigic_geonode

RUN apt-get update -y && apt-get install curl wget unzip gnupg2 locales -y

RUN apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

COPY src/celery.sh /usr/bin/celery-commands
RUN chmod +x /usr/bin/celery-commands

COPY src/celery-cmd /usr/bin/celery-cmd
RUN chmod +x /usr/bin/celery-cmd

COPY src/requirements.txt requirements.txt
RUN yes w | pip install -r requirements.txt
COPY src /usr/src/sigic_geonode/
RUN chmod +x /usr/src/sigic_geonode/tasks.py
RUN chmod +x /usr/src/sigic_geonode/entrypoint.sh
RUN yes w | pip install -e .

EXPOSE 8000