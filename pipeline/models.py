import uuid
import hashlib
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# Importamos las utilidades de procesamiento y el motor de estabilidad
from .utils import calculate_sha256, asset_version_path, get_video_metadata
from .divergence_engine import PipelineStabilityIndex

# Inicializamos el motor a nivel de módulo
engine = PipelineStabilityIndex()

# --- 1. Perfil de Usuario (Roles) ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='Artist') 
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

# --- 2. Licencia (Legal) ---
class License(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.name

# --- 3. Proyecto (Contenedor Principal) ---
class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Parámetros de Control de Calidad (QC)
    target_fps = models.FloatField(default=24.0)
    target_width = models.PositiveIntegerField(default=1920)
    target_height = models.PositiveIntegerField(default=1080)
    
    license = models.ForeignKey(License, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title

# --- 4. Asset (Entidad Lógica) ---
class Asset(models.Model):
    name = models.CharField(_("Asset Name"), max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assets')
    checksum_sha256 = models.CharField(_("SHA-256 Checksum"), max_length=64, unique=True, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'project')

    def __str__(self):
        return f"{self.name} [{self.project.title}]"

# --- 5. Version (Instancia Física) ---
class Version(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING_REVIEW = 'PENDING_REVIEW', _('Pending Review')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        DEPRECATED = 'DEPRECATED', _('Deprecated')

    class TranscodingStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        ERROR = 'ERROR', _('Error')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Metadatos Técnicos
    resolution_width = models.PositiveIntegerField(null=True, blank=True)
    resolution_height = models.PositiveIntegerField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, verbose_name=_("Duration (sec)"))
    filesize = models.BigIntegerField(null=True, blank=True, verbose_name=_("File Size (bytes)"))
    color_space = models.CharField(max_length=500, default='ACEScg') 
    timecode_start = models.CharField(max_length=11, default="00:00:00:00")

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='versions', verbose_name=_("Asset"))
    version_number = models.PositiveIntegerField() 
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING_REVIEW)
    transcoding_status = models.CharField(max_length=20, choices=TranscodingStatus.choices, default=TranscodingStatus.PENDING)

    file = models.FileField(_("Original File"), upload_to=asset_version_path, max_length=1000) 
    proxy_file_path = models.CharField(max_length=1000, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', max_length=1000, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Version")
        verbose_name_plural = _("Versions")
        unique_together = ('asset', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.asset.name} - v{self.version_number}"

    # --- Lógica de Negocio y Sensores de Estabilidad ---

    def ingest_and_verify(self, file_path):
        """Extrae ADN del archivo y reporta salud."""
        try:
            # 1. Sensor de Integridad
            generated_hash = calculate_sha256(file_path)
            is_integrity_ok = not (self.asset.checksum_sha256 and self.asset.checksum_sha256 != generated_hash)
            engine.report_status('integrity', success=is_integrity_ok)
            
            self.asset.checksum_sha256 = generated_hash
            self.asset.save()
            
            # 2. Sensor de Almacenamiento/Metadatos
            meta = get_video_metadata(file_path)
            if meta:
                # RELLENAMOS LOS DATOS CAPTURADOS
                self.resolution_width = meta.get('width')
                self.resolution_height = meta.get('height')
                self.fps = meta.get('fps')
                self.duration = meta.get('duration')
                self.color_space = meta.get('color_space', 'ACEScg') # <--- Captura Color Space
                
                # Capturamos tamaño de archivo real
                if os.path.exists(file_path):
                    self.filesize = os.path.getsize(file_path)
                
                self.save(update_fields=[
                    'resolution_width', 'resolution_height', 'fps', 
                    'duration', 'filesize', 'color_space'
                ])

                engine.report_status('storage', success=True)
                return True
            else:
                engine.report_status('storage', success=False)
                return False

        except Exception:
            engine.report_status('database', success=False)
            return False

    def check_qc(self):
        project = self.asset.project
        errors = []
        
        # Si falta información técnica, es un fallo de ingesta
        if not self.fps or not self.resolution_width:
            errors.append("Error de Ingesta: No se pudieron extraer metadatos técnicos.")
            return errors

        if abs(self.fps - project.target_fps) > 0.01:
            errors.append(f"FPS: {self.fps} (Esperado: {project.target_fps})")
            
        if (self.resolution_width != project.target_width or 
            self.resolution_height != project.target_height):
            errors.append(f"Res: {self.resolution_width}x{self.resolution_height}")
            
        return errors

    def clean(self):
        # 1. QC Original (Aprobación)
        if self.approval_status == self.ApprovalStatus.APPROVED:
            qc_errors = self.check_qc()
            if qc_errors:
                # Corregido: No usamos f-strings dentro de _()
                error_msg = _("QC fallido: {errors}").format(errors=', '.join(qc_errors))
                raise ValidationError({'approval_status': error_msg})

        # 2. Bloqueo de Duplicados (Uso eficiente de memoria)
        if self.file and not self.pk: # Solo validamos en subidas nuevas
            sha256_hash = hashlib.sha256()
            
            # Leemos el archivo en pedazos para no saturar la RAM
            for chunk in self.file.chunks():
                sha256_hash.update(chunk)
            
            nuevo_hash = sha256_hash.hexdigest()
            
            # Importante: Regresar el puntero al inicio para que Django pueda guardarlo
            self.file.seek(0)

            # Comparamos contra el hash "oficial" del Asset
            if self.asset.checksum_sha256 == nuevo_hash:
                raise ValidationError({
                    'file': _("Error de Redundancia: Este contenido ya es idéntico al archivo actual del Asset.")
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# --- 6. Comentarios ---
class Comment(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    frame_number = models.PositiveIntegerField(_("Frame"), null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)