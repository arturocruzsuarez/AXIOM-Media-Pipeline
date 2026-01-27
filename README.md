# AXIOM: Cloud-Native Media Pipeline

**AXIOM** is a high-performance Digital Asset Management (DAM) system specifically architected for VFX and Animation production environments. The system focuses on absolute data integrity, automated Quality Control (QC) orchestration, and atomic version traceability.

> **Status:** Active Development (v0.1.0)  
> **Role:** Lead Backend Engineer & Architect (Target: Aspiring Pipeline TD)

---

## 🚀 Key Features (Implemented & Functional)

* **Cryptographic Integrity ($SHA-256$):** Implementation of binary-level hashing for every ingested asset. This ensures bit-perfect integrity and enables intelligent data de-duplication across the storage layer.
* **Automated Technical QC:** Real-time metadata extraction using `PyMediaInfo`. The system automatically validates resolution, FPS, and color space against project-specific targets, triggering instant **PASS/FAIL** status.
* **Dynamic Media Engine (FFmpeg):** Automated creation of 720p H.264 review proxies and frame-accurate thumbnails via FFmpeg subprocesses during the ingest phase.
* **Atomic Versioning:** Industry-standard versioning logic (`v001`, `v002`) to enforce a **Single Source of Truth (SSOT)** and prevent naming collisions.

---

## 🛠️ Tech Stack

### **Current Core**
* **Backend:** Python 3.10+, Django 5.0.
* **Media Processing:** FFmpeg (Transcoding), PyMediaInfo (Technical Metadata).
* **Database:** PostgreSQL (Production-ready) / SQLite (Development).

### **Architecture Roadmap (Upcoming Features)**
* **Distributed Task Queue:** Decoupling heavy transcoding loads from the web server using **Celery** and **Redis**.
* **Containerization:** Full infrastructure orchestration via **Docker** and **Kubernetes**.
* **Cloud Storage:** Native **AWS S3** integration for high-availability asset storage.

---

## 🏗️ Pipeline Architecture

AXIOM follows an event-driven state flow to ensure no asset reaches a supervisor without passing technical validation:



1.  **Ingest Layer:** Enforces naming conventions and calculates the file's unique digital fingerprint.
2.  **Validation Layer:** Compares real-time binary metadata against project requirements.
3.  **Processing Layer:** Orchestrates FFmpeg instances to generate lightweight review media.
4.  **Persistence Layer:** Updates the PostgreSQL registry with proxy paths and final QC states.

---

## 📚 Technical Documentation

For a detailed analysis of the system's architecture diagram and its alignment with industry standards (MovieLabs 2030), please refer to the following specification:

📄 [**Download AXIOM Architecture Specification (PDF)**](docs/AXIOM_Architecture_Spec.pdf)

---

## 📦 Setup & Installation

### **Prerequisites**
* **FFmpeg:** Must be installed and available in the system PATH (Standard in WSL/Linux).
* **MediaInfo:** Required for technical metadata extraction.

### **Quick Start**
```bash
# 1. Clone the repository
git clone [https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git](https://github.com/arturocruzsuarez/AXIOM-Media-Pipeline.git)

# 2. Setup Virtual Environment
python -m venv venv
source venv/bin/activate  # On WSL/Linux

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Run Database Migrations
python manage.py migrate

# 5. Start Development Server
python manage.py runserver

Developed by Arturo C.S. - Computer Engineering Student & Aspiring Pipeline TD.
