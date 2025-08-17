ARG BASE_IMAGE_VERSION
FROM geonode/geoserver:${BASE_IMAGE_VERSION}

# COPY gs-wps-download-excel/target/gs-wps-download-excel-1.0.0.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/

COPY geoserver-2.24.4-excel-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-ogr-wps-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY geoserver-2.24.4-ogr-wfs-plugin/*.jar /usr/local/tomcat/webapps/geoserver/WEB-INF/lib/
COPY ogr2ogr.xml /geoserver_data/data
