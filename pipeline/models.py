import uuid
import hashlib
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError  
from django.db.models import Max
from django.db import transaction

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
    # Añadimos categorías para ser agnósticos al formato
    class AssetCategory(models.TextChoices):
        VIDEO = 'VIDEO', _('Video/Footage')
        MODEL_3D = '3D', _('3D Model/Asset')
        AUDIO = 'AUDIO', _('Audio/Score')
        CODE = 'CODE', _('Script/Tool')
        IMAGE = 'IMAGE', _('Texture/Concept')
        OTHER = 'OTHER', _('Generic Data')
        
    name = models.CharField(_("Asset Name"), max_length=255) 
    category = models.CharField(
        max_length=10, 
        choices=AssetCategory.choices, 
        default=AssetCategory.VIDEO
    )
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
    
    # En pipeline/models.py


    class Department(models.TextChoices):
        EDITORIAL = 'ED', _('Editorial')
        LAYOUT = 'LAY', _('Layout')
        ANIMATION = 'ANIM', _('Animation')
        FX = 'FX', _('Effects')
        LIGHTING = 'LGT', _('Lighting')
        COMPOSITING = 'COMP', _('Compositing')
        ART = 'ART', _('Art/Concept')
        GENERIC = 'GEN', _('Generic/Asset')

    # Nuevo campo de departamento
    department = models.CharField(
        max_length=4,
        choices=Department.choices,
        default=Department.GENERIC,
        verbose_name=_("Department")
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Metadatos Técnicos
    resolution_width = models.PositiveIntegerField(null=True, blank=True)
    resolution_height = models.PositiveIntegerField(null=True, blank=True)
    # Métricas técnicas (Opcionales para soportar Stills/Footage/Assets)
    fps = models.FloatField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, verbose_name=_("Duration (sec)"))
    filesize = models.BigIntegerField(null=True, blank=True, verbose_name=_("File Size (bytes)"))
    
    # Espacio de color: ACEScg es ideal, pero mejor dejar que el sistema lo detecte
    color_space = models.CharField(max_length=500, null=True, blank=True) 
    
    # El timecode solo existe en video; en imágenes debe ser nulo
    timecode_start = models.CharField(max_length=11, null=True, blank=True) 
    
    extra_metadata = models.JSONField(default=dict, blank=True)

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='versions', verbose_name=_("Asset"))
    version_number = models.PositiveIntegerField(blank=True, null=True) 
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING_REVIEW)
    transcoding_status = models.CharField(max_length=20, choices=TranscodingStatus.choices, default=TranscodingStatus.PENDING)

    file = models.FileField(_("Original File"), upload_to=asset_version_path, max_length=1000) 
    proxy_file_path = models.FileField(max_length=1000, blank=True, null=True)
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
        """Extrae ADN del archivo de forma agnóstica para cumplir con el SSOT."""
        try:
            # 1. Sensor de Integridad (Universal)
            # Esto se ejecuta para TODO archivo, cumpliendo con la "Higiene de Datos"
            generated_hash = calculate_sha256(file_path)
            
            # Verificamos si el hash coincide con lo que el sistema espera (SSOT)
            is_integrity_ok = not (self.asset.checksum_sha256 and self.asset.checksum_sha256 != generated_hash)
            engine.report_status('integrity', success=is_integrity_ok) 
            
            if not Asset.objects.filter(checksum_sha256=generated_hash).exclude(id=self.asset.id).exists():
                self.asset.checksum_sha256 = generated_hash
                self.asset.save()
            else:
                return False # Evitamos el crash y salimos pacíficamente
            
            # El Asset (entidad lógica) guarda la "verdad" del contenido
            #self.asset.checksum_sha256 = generated_hash
            #self.asset.save()
            
            # 2. Captura de datos físicos básicos (Agnóstico)
            if os.path.exists(file_path):
                self.filesize = os.path.getsize(file_path)
            
            # Preparamos la lista de campos a actualizar para optimizar el guardado
            fields_to_update = ['filesize', 'extra_metadata']
            
            # 3. Sensor de Metadatos (Específico vs Genérico)
            # Solo intentamos extraer data de video si la categoría es VIDEO
            if self.asset.category == Asset.AssetCategory.VIDEO:
                meta = get_video_metadata(file_path)
                if meta:
                    self.resolution_width = meta.get('width')
                    self.resolution_height = meta.get('height')
                    self.fps = meta.get('fps')
                    self.duration = meta.get('duration')
                    self.color_space = meta.get('color_space', 'ACEScg')
                    
                    # Guardamos el dump completo en extra_metadata por si necesitamos algo luego
                    self.extra_metadata['video_raw_info'] = meta 
                    self.timecode_start = meta.get('timecode_start')
                    
                    fields_to_update.extend([
                        'resolution_width', 'resolution_height', 
                        'fps', 'duration', 'color_space', 'timecode_start'
                    ])
                    engine.report_status('storage', success=True)
                else:
                    # Si es video pero falla la extracción (ej. archivo corrupto)
                    engine.report_status('storage', success=False)
            else:
                # Si es un activo 3D, Código o Audio, marcamos éxito basándonos en la integridad
                self.extra_metadata['ingest_type'] = 'agnostic_transfer'
                engine.report_status('storage', success=True)

            # 4. Guardado atómico de la versión
            #self.save(update_fields=fields_to_update) 
            #if self.asset.category in [Asset.AssetCategory.VIDEO, Asset.AssetCategory.IMAGE]:
                # Usamos on_commit para que Celery no empiece antes de que Django termine el SAVE
             #   from .tasks import process_media_task
              #  transaction.on_commit(
               #     lambda: process_media_task.delay(self.uuid) 
                #)
                # Nota: Usamos self.uuid porque es el identificador único que definiste
            
            self.save(update_fields=fields_to_update)
            return True

        except Exception as e:
            import traceback
            print("🛑 ERROR CRÍTICO EN INGESTA:")
            traceback.print_exc()  # Esto desnudará el error en tu terminal
            
            engine.report_status('database', success=False)
            return False

    def check_qc(self):
        """
        Validación de Calidad (QC) diferenciada.
        Asegura que cada activo cumpla con los estándares del proyecto según su tipo.
        """
        project = self.asset.project
        errors = []
        
        # --- BLOQUE 1: QC PARA VIDEO ---
        # Solo ejecutamos estas validaciones si el activo es de categoría VIDEO
        if self.asset.category == Asset.AssetCategory.VIDEO:
            # Validación de metadatos mínimos extraídos por FFprobe
            if not self.fps or not self.resolution_width:
                errors.append(_("Error de Ingesta: No se detectaron parámetros técnicos de video."))
                return errors

            # Validación de FPS contra el Target del Proyecto
            if abs(self.fps - project.target_fps) > 0.01:
                errors.append(f"FPS: {self.fps} (Esperado: {project.target_fps})")
            
            # Validación de Resolución contra el Target del Proyecto
            if (self.resolution_width != project.target_width or 
                self.resolution_height != project.target_height):
                errors.append(f"Resolución: {self.resolution_width}x{self.resolution_height} (Esperada: {project.target_width}x{project.target_height})")

        # --- BLOQUE 2: QC PARA CÓDIGO (Ejemplo de expansión) ---
        elif self.asset.category == Asset.AssetCategory.CODE:
            # Ejemplo: Validar que no sea un archivo vacío
            if self.filesize and self.filesize == 0:
                errors.append(_("Error: El archivo de script está vacío."))
        
        # --- BLOQUE 3: QC GENÉRICO (Integridad SSOT) ---
        # Independientemente del tipo, si no hay Checksum, no hay Verdad Única
        if not self.asset.checksum_sha256:
            errors.append(_("Error de Integridad: El activo no posee un hash SHA-256 validado."))

        return errors

    def clean(self):
        # 1. QC Original (Aprobación)
        if self.approval_status == self.ApprovalStatus.APPROVED:
            qc_errors = self.check_qc()
            if qc_errors:
                error_msg = _("QC fallido: {errors}").format(errors=', '.join(qc_errors))
                raise ValidationError({'approval_status': error_msg})

        # 2. Bloqueo de Duplicados (Uso eficiente de memoria)
        if self.file and not self.pk: 
            sha256_hash = hashlib.sha256()
            for chunk in self.file.chunks():
                sha256_hash.update(chunk)
            nuevo_hash = sha256_hash.hexdigest()
            self.file.seek(0)

            # --- LA MEJORA CLAVE AQUÍ ---
            # Buscamos si el hash ya existe en CUALQUIER otro Asset del sistema
            # Esto evita el error de "Unique Constraint" que te salió
            asset_duplicado = Asset.objects.filter(checksum_sha256=nuevo_hash).exclude(id=self.asset.id).first()
            
            if asset_duplicado:
                raise ValidationError({
                    'file': _(f"Error de Integridad: Este archivo ya es la 'Fuente de Verdad' del Asset: '{asset_duplicado.name}'. "
                              "En AXIOM, no puedes duplicar material entre diferentes Assets.")
                })

            # 3. Comparación contra el hash actual del mismo Asset (Redundancia)
            if self.asset.checksum_sha256 == nuevo_hash:
                raise ValidationError({
                    'file': _("Error de Redundancia: Este contenido ya es idéntico a la versión actual de este Asset.")
                })

    def save(self, *args, **kwargs):
        # 1. Si es una versión nueva (no tiene ID) y no tiene número asignado...
        if not self.pk and self.version_number is None:
            from django.db.models import Max
            # Buscamos el número más alto para este activo específico (Asset)
            last_v = Version.objects.filter(asset=self.asset).aggregate(Max('version_number'))['version_number__max']
            self.version_number = (last_v + 1) if last_v else 1
            
        # 2. Ahora que ya tiene número, la validación ya no fallará
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
    
class SystemHealth(models.Model):
    """Almacena el estado técnico global del Pipeline."""
    storage_score = models.FloatField(default=100.0)
    database_score = models.FloatField(default=100.0)
    ffmpeg_score = models.FloatField(default=100.0)
    integrity_score = models.FloatField(default=100.0)
    last_diagnostic = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Health"
        verbose_name_plural = "System Health"

    def __str__(self):
        return f"Health Status: {self.last_diagnostic.strftime('%Y-%m-%d %H:%M')}"