# Базовый образ с miniforge3 (libmamba уже встроен по умолчанию)
#FROM dockerhub.timeweb.cloud/continuumio/miniconda3:latest
FROM dockerhub.timeweb.cloud/condaforge/miniforge3:latest

# Установка системных пакетов
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    nano \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Настройка системного конфига Conda с зеркалами Tsinghua TUNA Китай
RUN rm -f ~/.condarc /opt/conda/.condarc /etc/conda/.condarc && \
    mkdir -p /etc/conda && \
    cat <<EOF > /etc/conda/.condarc
channels:
  - conda-forge
  - defaults
show_channel_urls: true
channel_priority: strict
solver: libmamba
use_jlap: false
default_channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
custom_channels:
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  bioconda: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
EOF

# Создание окружения с Python 3.11
RUN conda clean -all -y && \
    conda create -n multicomp python=3.11 -y && \
    conda clean -afy

# Активация окружения по умолчанию
ENV PATH=/opt/conda/envs/multicomp/bin:$PATH

# Установка Python-пакетов (без флага -c conda-forge, чтобы работал /etc/conda/.condarc)
RUN conda install -n multicomp \
    django \
    django-filer \
    django-mptt \
    django-cleanup \
    gdal \
    numpy==1.26.4 \
    psycopg2 \
    gunicorn \
    typing_extensions \
    -y && \
    conda clean -afy

WORKDIR /app
COPY . /app/

# Настройка nginx
COPY nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Настройка supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

