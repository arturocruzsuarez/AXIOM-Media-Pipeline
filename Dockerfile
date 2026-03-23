# Imagen base estable
FROM python:3.12-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalamos dependencias del sistema incluyendo FFmpeg y MediaInfo
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    libmediainfo-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Instalamos las librerías de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . /app/

# Exponemos el puerto de Django
EXPOSE 8000