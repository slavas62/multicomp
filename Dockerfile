
# Базовый образ с conda
FROM continuumio/miniconda3:latest

# Установка системных пакетов: nginx, supervisor и библиотеки для PostgreSQL
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    nano \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем механизм разрешения зависимостей в менеджере пакетов Conda - новый libmamba (быстрый) старый classic (медленый)
RUN conda install conda-libmamba-solver
RUN conda config --set solver libmamba
#RUN conda config --set solver classic

# Создание conda-окружения с Python 3.11
RUN conda create -n multicomp python=3.11 -y && \
    conda clean -afy

# Активация окружения по умолчанию
ENV PATH=/opt/conda/envs/multicomp/bin:$PATH

# Установка всех необходимых Python‑пакетов через conda (включая gdal, numpy, psycopg2), где numpy==1.26.4 старая версия, которую поддерживают старые сервера в ЦОД РКС
RUN conda install -n multicomp -c conda-forge \
    django \
    django-filer \
    django-mptt \
    django-cleanup \
    gdal \
    numpy==1.26.4 \
    psycopg2 \
    gunicorn \
    -y && \
    conda clean -afy

# Рабочая директория внутри контейнера
WORKDIR /app

# Копирование исходного кода проекта
COPY . /app/


# Настройка nginx
COPY nginx.conf /etc/nginx/sites-available/default
RUN rm /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Настройка supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Сбор статики Django (предполагается, что STATIC_ROOT настроен)
#RUN python manage.py collectstatic --noinput
# Выполнение миграций БД
#RUN python manage.py migrate --fake-initial --noinput

# Порт, который будет слушать nginx
EXPOSE 80

# Запуск supervisor (управляет gunicorn и nginx)
#CMD ["supervisord", "-n"]

# Копирование и подготовка entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]