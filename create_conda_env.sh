#!/bin/bash

# Запуск скрипта создания виртуальной среды и проекта Django. !!! Только после установки Miniconda3 в ОС  -
# Синтаксис команды -  . create_conda_env.sh {envname}, 
# где, {envname) - имя виртуального окружения и проекта Django (формальный параметр $1)

# Инициализация conda для текущей сессии оболочки.
eval "$(conda shell.bash hook)"

# Установка Miniconda3 на Linux
# wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
# bash /tmp/miniconda.sh

# 1. Создаём виртуальное окружение, где $1 - имя окружения (по умолчанию будет установлена в папку ~/miniconda3/envs/$1/)
conda create -y -n $1 python=3.11 -c conda-forge

# 2. Активируем виртуальную среду
conda activate $1

# 3. Устанавливаем Django и гео-библиотеки GDAL и numpy из conda-forge
conda install -y django django-filer django-mptt django-cleanup gdal numpy -c conda-forge
python -c "from osgeo import gdal, gdal_array; print(gdal.__version__)" # проверяем корректность установки, 
python -m django --version                                              # если все ок, то выводится версия GDAL и Django

# 5. Создаем проект django с именем $1 в папке ~/miniconda3/envs/{$1}/
cd ~/miniconda3/envs/$1
django-admin startproject $1

# 6. Устанавливаем дополнительные библиотеки через pip
#conda install python pip      # Ставим основу
pip install psycopg2            # Ставим  через pip то, что не ставится через conda
#pip install django-polymorphic
#pip install easy_thumbnails
