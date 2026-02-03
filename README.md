# 📟 AXIOM | Media Asset Pipeline & Divergence Engine

**AXIOM** is an industrial-grade Media Asset Management (MAM) system designed specifically for VFX and film production environments. It goes beyond simple file hosting by auditing the technical integrity of every bit and visualizing production stability through a custom **Divergence Engine** inspired by Nixie tube aesthetics.

---

## 🚀 Key Features

### 📈 Nixie-Powered Divergence Engine
A real-time monitoring system that calculates the **Pipeline Stability Index (PSI)**.
* **Dynamic Telemetry:** The meter fluctuates based on integrity checks, QC failures, and data redundancy.
* **High-End UI:** A 3D Nixie tube visualization featuring glass-morphism, glow effects, and real-time flicker.

### 🛡️ Data Integrity & Deduplication
* **SHA-256 Hashing:** The system implements a "Storage-Aware" architecture that automatically blocks duplicate uploads by comparing cryptographic hashes, significantly optimizing server storage.
* **VFX Hierarchy:** Built on a strict industry-standard logic: `Project > Asset > Version > Comment`.
* **Role-Based Access Control:** Artists operate in a technical read-only environment, while Supervisors hold full authority over Quality Control (QC) and approval status.

### ⚙️ Automated "Video DNA" Extraction
Leveraging **FFmpeg** and **MediaInfo** to automatically extract and validate:
* **Resolution & FPS:** Real-time validation against project-specific targets.
* **Color Space:** Automatic detection of pixel formats (YUV, ACEScg, sRGB, etc.).
* **Duration & File Size:** Precise tracking down to the millisecond and byte level.

---

## 🛠️ Tech Stack

* **Backend:** Django (Python 3.x)
* **Distributed Processing:** Celery + Redis
* **Video Engine:** FFmpeg / PyMediaInfo
* **Database:** PostgreSQL / SQLite
* **Frontend:** HTML5 (Canvas/JS for the Nixie Engine), CSS3 (VFX Glassmorphism)

---

## 🏗️ System Architecture

The pipeline utilizes a micro-service-oriented architecture to ensure video processing never bottlenecks the user interface.

1. **Ingest:** User uploads an asset via the Django Admin.
2. **Validation:** The `clean()` method executes a SHA-256 hash check to prevent redundancy.
3. **Task Queue:** Celery receives the Version UUID and triggers a background metadata analysis.
4. **Telemetry:** The **Divergence Engine** updates the global PSI based on the health of the incoming data.

---

## 📋 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git](https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git)
   cd AXIOM-Media-Pipeline

# 2. Setup Virtual Environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Launch Services:
Redis: redis-server

Worker: celery -A AXIOM worker --loglevel=info

Migrate: python manage.py migrate

Server: python manage.py runserver


Developed by Arturo C.S. - Computer Engineering Student & Aspiring Pipeline TD.
