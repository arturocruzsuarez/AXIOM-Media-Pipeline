# 📟 AXIOM | Production Asset Pipeline & Divergence Engine

**AXIOM** is an industrial-grade **Production Asset Management (PAM)** ecosystem designed under the **Single Source of Truth (SSOT)** principles of the MovieLabs 2030 vision. It is specifically engineered for high-velocity VFX and film production environments, auditing the technical integrity of every bit and visualizing pipeline stability through a custom **Divergence Engine**.

---

## 🚀 Key Features

### 🛡️ Production Data Integrity (SSOT)
* **SHA-256 Hashing:** A "Storage-Aware" architecture that automatically blocks duplicate version uploads by comparing cryptographic hashes, optimizing production storage and ensuring a clean SSOT.
* **VFX Hierarchy:** Data structure strictly aligned with studio standards: `Project > Asset > Version > Comment`.
* **Technical Validation:** Automatic extraction and validation of Color Spaces (ACEScg, sRGB), FPS, and Resolution via **FFmpeg** and **MediaInfo**.

### 📈 Nixie-Powered Divergence Engine
A real-time monitoring system that calculates the **Pipeline Stability Index (PSI)**.
* **Dynamic Telemetry:** The meter fluctuates based on integrity checks, service health, and ingestion success rates across the production floor.
* **High-End UI:** A specialized interface featuring glass-morphism, glow effects, and real-time flicker to visualize the "health" of the production pipeline.

### 🔌 DCC Agnostic Connector
Includes a communication bridge (`scripts/publish_tool.py`) successfully tested for direct integration with **Blender, Maya, and Nuke**. It allows artists to "Publish" iterations directly from their workstation to the centralized PAM server via REST API.

---

## 🏗️ System Architecture (Microservices)

AXIOM utilizes a microservice-oriented architecture managed via **Docker** to ensure that heavy video processing (FFmpeg) and metadata extraction never bottlenecks the user interface.

* **Django:** Core API, business logic, and production management.
* **PostgreSQL:** Technical data and asset persistence.
* **Redis:** High-speed message broker for asynchronous tasks.
* **Celery:** Processing engine for background "Video DNA" extraction and thumbnail generation.

---

## 🛠️ Installation & Setup (Dockerized)

The fastest way to deploy the ecosystem is using containers:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git](https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git)
   cd AXIOM-Media-Pipeline 

2. **Launch Ecosystem:**
   ```bash 
   docker-compose up --build 

3. **Generate API Token (Required for DCC Scripts):**
   ```bash 
   docker-compose exec web python manage.py drf_create_token arturocs 

### DCC Integration

1.- Configure your TOKEN in scripts/publish_tool.py.

2.- Define your render path in video_path.

To test the asset ingestion from any workstation (Windows/Linux/MacOS/Blender/Maya), use the provided Python client. This tool validates files and communicates with the REST API:

3. **Ingestion Test**
   ```bash
   python scripts/publish_tool.py --file "path/to/your/video.mp4" --asset "Hero_Asset" --token "YOUR_TOKEN"

4.- Run: python scripts/publish_tool.py.

5.- The Divergence Dashboard will update automatically, reflecting the new version and the integrity of the production asset.  


Developed by Arturo C.S. - Computer Engineering Student @ UAM Cuajimalpa | Aspiring Pipeline TD.