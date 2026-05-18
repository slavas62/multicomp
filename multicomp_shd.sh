#!/bin/sh
set -e

# Хранилище докер контейнера
IMAGE=slavas/multicomp:debian
USER='postgres'
PASS='ntnhfrcby_19'

# Имя докер контейнера
CONTAINER_NAME=multicomp

# Имя домена 3-го уровня
DOMAIN=appsgeotron.spacecorp.ru

# Порт
PORT=80

# Загружаем образ контейнера
docker pull $IMAGE

# Останавливаем и удаляем старый контейнер
docker stop $CONTAINER_NAME || true && docker rm $CONTAINER_NAME || true

# Create multicomp work DIRECTORY
SHD=/mnt/share
DIR=/home/ncomz/data/$CONTAINER_NAME
if [ ! -d $DIR ] 
then
    mkdir $DIR
    sudo chmod -R 775 $DIR
fi

# Запускаем новый контейнер (БД Postgres16-3.4 находится на ЦОД ВМ-3 Резерв по адресу '10.200.129.15')
docker run \
   --name $CONTAINER_NAME \
   -d \
   --restart=always \
\
   -e VIRTUAL_HOST=$CONTAINER_NAME.$DOMAIN \
\
   -e DB_SYS_NAME=$CONTAINER_NAME \
   -e DB_HOST_URL='10.200.129.15' \
   -e DB_PORT_VAL=5432 \
   -e DB_USER_NAME=$USER \
   -e DB_PASSWORD=$PASS \
\
   -e GEOSERVER_GEOTRON_WORKSPACE='$CONTAINER_NAME' \
   -e GEOSERVER_DEFAULT_URL='http://172.17.0.1:8080/' \
   -e GEOSERVER_DEFAULT_USERNAME='admin' \
   -e GEOSERVER_DEFAULT_PASSWORD='ntnhfrcby_19' \
\
   -e PROJ_LIB='/opt/conda/envs/multicomp/share/proj' \
\
   -v $SHD/$CONTAINER_NAME/media:/app/media \
   -v $SHD/geoserver-226/geodata/multicomp:/app/media/composite \
   -v $DIR/logs:/var/log \
   -v $DIR/logs/nginx:/var/log/nginx \
\
   -e DJANGO_DEBUG=False \
$IMAGE

#   -p $PORT:80 \
