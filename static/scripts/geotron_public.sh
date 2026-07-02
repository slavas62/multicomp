#!/bin/sh
set -e

WORKSPACE=multicomp

FILE=geodata/$WORKSPACE/$1  # полный путь файла композита в папке геосервера виртуалки
FILENAME="${FILE##*/}"      # имя файла с расширением

REST_URL=http://172.17.0.1:8080/geoserver/rest # URL геосервера и
AUTH=$2                                        # логин:пароль для входа на геосервер (AUTH)
#AUTH=admin:geoserver

STORETYPE=GeoTIFF
STORENAME="${FILENAME%.*}"   # имя файла без расширения

PROJ=EPSG:3857
PROJ_POL=FORCE_DECLARED  # FORCE_DECLARED (оставить объявленную), REPROJECT_TO_DECLARED (преобразовать родную в объявленную), NONE (сохранить родную)

# 1. Создаем рабочее пространство
curl -u $AUTH -XPOST -H "Content-type: application/xml" -d "<workspace><name>$WORKSPACE</name></workspace>" $REST_URL/workspaces

# 2. Создаем хранилище 226
curl -u $AUTH -XPOST -H "Content-Type: application/xml" -d "<coverageStore><name>$STORENAME</name><type>$STORETYPE</type><url>$FILE</url><workspace>$WORKSPACE</workspace><enabled>true</enabled></coverageStore>" $REST_URL/workspaces/$WORKSPACE/coveragestores

# 3. Создаем слой 226
curl -u $AUTH -XPOST -H "Content-Type: application/xml" -d "<coverage><name>$STORENAME</name><title>МВК НЦ ОМЗ</title><projectionPolicy>$PROJ_POL</projectionPolicy></coverage>" $REST_URL/workspaces/$WORKSPACE/coveragestores/$STORENAME/coverages