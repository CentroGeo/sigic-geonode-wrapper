#!/bin/sh

mvn install:install-file \
  -Dfile=lib/gs-main-2.24.4.jar \
  -DgroupId=org.geoserver \
  -DartifactId=gs-main \
  -Dversion=2.24.4 \
  -Dpackaging=jar

mvn install:install-file \
  -Dfile=lib/gs-wps-core-2.24.4.jar \
  -DgroupId=org.geoserver \
  -DartifactId=gs-wps-core \
  -Dversion=2.24.4 \
  -Dpackaging=jar

mvn install:install-file \
  -Dfile=lib/gs-wps-download-2.24.4.jar \
  -DgroupId=org.geoserver \
  -DartifactId=gs-wps-download \
  -Dversion=2.24.4 \
  -Dpackaging=jar
