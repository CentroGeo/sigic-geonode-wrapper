ARG BASE_IMAGE_VERSION
FROM geonode/geoserver:${BASE_IMAGE_VERSION}

RUN apt-get update && apt-get install -y gdal-bin && rm -rf /var/lib/apt/lists/*

# COPY gs-wps-download-excel/target/gs-wps-download-excel-1.0.0.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-excel-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-ogr-wps-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-ogr-wfs-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY ogr2ogr.xml entrypoint.sh /usr/local/tomcat/tmp/

RUN chmod +x /usr/local/tomcat/tmp/entrypoint.sh

# CMD ["/usr/local/tomcat/tmp/entrypoint.sh"]