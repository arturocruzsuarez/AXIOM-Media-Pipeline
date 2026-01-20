# AXIOM: Cloud-Native Media Pipeline

**AXIOM** es un sistema de gestión de activos digitales (DAM) de alto rendimiento diseñado para flujos de trabajo de VFX y Animación. Implementa una arquitectura **Producer-Consumer** para la ingesta, transcodificación y versionado atómico de material audiovisual.

> **Status:** Active Development (v0.1.0)
> **Role:** Lead Backend Engineer & Architect

## 🚀 Key Features

* **Atomic Versioning:** Implementación de "Single Source of Truth" (SSOT) para garantizar la integridad referencial entre versiones de corte (`v001`, `v002`) y sus metadatos.
* **Asset Lineage:** Sistema de trazabilidad (`parent_version`) que permite derivar nuevas versiones a partir de cualquier punto en el historial, permitiendo "rollbacks" seguros sin pérdida de datos.
* **Asynchronous Processing Engine:** Orquestación de tareas pesadas (transcodificación de video) mediante **Celery** y **Redis**, desacoplando la carga del servidor web para una respuesta HTTP inmediata (202 Accepted).
* **Low-Level Media Manipulation:** Uso de **FFmpeg** a través de `subprocess` para control granular sobre codecs (H.264), contenedores y extracción de metadatos técnicos.

## 🛠️ Tech Stack

* **Core:** Python 3.10+, Django 5.0 (Django REST Framework)
* **Database:** PostgreSQL (Production), SQLite (Dev)
* **Async Task Queue:** Celery 5.3 + Redis (Broker)
* **Media Engine:** FFmpeg
* **Infrastructure:** Docker support (Planned), AWS S3 Integration (In Progress)

## 🏗️ Architecture Overview

The system follows a modular architecture inspired by Netflix's microservices patterns for studio technologies:

1.  **Ingest API:** Validates asset integrity and enforces strict naming conventions.
2.  **Task Dispatcher:** Serializes the request and pushes jobs to the Redis queue.
3.  **Worker Nodes:** Consumes tasks to perform CPU-intensive transcoding operations without blocking the main thread.
4.  **Persistence Layer:** Updates the PostgreSQL database with transactional integrity upon task completion.

## 📦 Setup & Installation

```bash
# Clone the repository
git clone [https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git](https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git)

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Migrations
python manage.py migrate

# Start Redis (Required for Async Tasks)
redis-server

# Start Celery Worker
celery -A cuajicine_api worker -l info

# Start Development Server
python manage.py runserver

Developed by Arturo C.S. - Computer Engineering Student & Aspiring Pipeline TD.
