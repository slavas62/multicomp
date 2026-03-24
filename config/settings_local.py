import os, sys
from pathlib import Path

DEBUG = True
INTERNAL_IPS = ('127.0.0.1',)

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'multicomp',   # name of system database
        'USER': 'postgres',
        'PASSWORD': 'ntnhfrcby_19',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

EMAIL_HOST = 'smtp.mail.ru'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'rss-geotron@bk.ru'
EMAIL_HOST_PASSWORD = 'Vhvryk9nAMv7ibwd1TEH' # 'FF62X5sg9wn9Lwb'
DEFAULT_FROM_EMAIL = 'rss-geotron@bk.ru'
BBP_ORDER_EMAIL = 'rss-geotron@bk.ru'

'''
BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

GEOSERVER_GEOTRON_WORKSPACE = 'geotron'
GEOSERVER_BBP_WORKSPACE = 'bbp'
GEOSERVER_DATA_PATH = None

GEOSERVER_DEFAULT_URL = 'http://172.17.0.1:8080/geoserver/'
GEOSERVER_DEFAULT_USERNAME = 'admin'
GEOSERVER_DEFAULT_PASSWORD = 'ntnhfrcby_19'

GEOSERVER_DATA_URL = 'http://172.17.0.1:8080/'
GEOSERVER_DATA_USERNAME = 'admin'
GEOSERVER_DATA_PASSWORD = 'vbs_3631'

ETRIS_DEFAULT_URL = 'https://gptl.ru/api'
ETRIS_DEFAULT_USERNAME = 'rekod2'
ETRIS_DEFAULT_PASSWORD = 'vbs_3631'
'''

ENV_DIR = ''
OGR_ENABLE_PARTIAL_REPROJECTION = False
