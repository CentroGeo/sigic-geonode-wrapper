# SPDX-FileCopyrightText: 2025 CentroGeo
# SPDX-FileContributor: César Benjamín <cesarbenjamindotnet@gmail.com>
# SPDX-License-Identifier: Apache-2.0
#
# Descripción:
#   Este Dockerfile extiende la imagen oficial de GeoNode/GeoServer:
#     - Instala GDAL (`gdal-bin`) para habilitar funcionalidades OGR.
#     - Copia los plugins adicionales:
#         * GeoPackage Output
#         * Excel Plugin
#         * OGR WPS Plugin
#         * OGR WFS Plugin
#     - Copia la configuración `ogr2ogr.xml` y scripts auxiliares al contenedor.
#     - Ajusta permisos de ejecución para scripts en `/usr/local/tomcat/tmp/`.

ARG BASE_IMAGE_VERSION
FROM geonode/geoserver:${BASE_IMAGE_VERSION}

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
