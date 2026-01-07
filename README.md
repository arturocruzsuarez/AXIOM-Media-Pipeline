# CuajiCine-PAM
**A Scalable Production Asset Management System**

CuajiCine is designed to solve the complexity of media asset lifecycles in film production. It acts as a central hub for version control, automated transcoding, and delivery of cinematic assets.

## 🏗️ Technical Stack
- **Framework:** Django (Python)
- **Task Queue:** Celery with Redis (Asynchronous media processing)
- **Engine:** FFmpeg (Automated transcoding pipelines)
- **Database:** PostgreSQL (Metadata management)

## 🚀 Key Features
- **Automated Ingest:** Automatic proxy generation for high-res footage.
- **Distributed Processing:** Scalable worker architecture for heavy video tasks.
- **API First:** Designed to integrate with DCC tools like Blender or Maya.

*Note: Core modules are currently being refactored for professional deployment. Documentation and source code updates in progress.*
