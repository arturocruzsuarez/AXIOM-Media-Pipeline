import uuid
import hashlib
import os
from django.db import models 
from django.conf import settings 
from django.utils import timezone
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
#class License(models.Model):
 #   name = models.CharField(max_length=100)
  #  description = models.TextField()
    
   # def __str__(self):
    #    return self.name

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
    
    #license = models.ForeignKey(License, on_delete=models.SET_NULL, null=True, blank=True)

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
    

def get_version_path(instance, filename):
    # 0. Verificación de seguridad inicial (Guard Clause)
    # Si por alguna razón la Versión no está ligada a un Asset aún,
    # evitamos que el sistema truene al intentar acceder a instance.asset.project
    if not instance.asset:
        return f"unsorted/{filename}"

    # 1. Preparación de variables (Sanitización)
    project_title = "unknown"
    if instance.asset.project:
        project_title = instance.asset.project.title.replace(" ", "_")
        
    category = instance.asset.category
    asset_name = instance.asset.name.replace(" ", "_")
    dept = instance.department if instance.department else "gen"
    
    # 2. Manejo de la versión
    v_num = instance.version_number
    if v_num is None:
        try:
            # Usamos instance.__class__ para evitar avisos de registro doble
            last_v = instance.__class__.objects.filter(
                asset=instance.asset, 
                department=instance.department
            ).order_by('version_number').last()
            v_num = (last_v.version_number + 1) if last_v else 1
        except:
            v_num = 1
    
    version_str = f"v{v_num:03d}"
    
    # 3. Nomenclatura Automática (Determinismo de datos)
    ext = os.path.splitext(filename)[1]
    new_filename = f"{project_title}_{asset_name}_{dept}_{version_str}{ext}"
    
    # 4. Retornar la ruta estructurada siguiendo el estándar industrial
    return f"projects/{project_title}/{category}/{asset_name}/{dept}/{version_str}/{new_filename}"

# --- 5. Version (Instancia Física) ---
class Version(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING_REVIEW = 'PENDING_REVIEW', _('Pending Review')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected') 
        CBB = 'CBB', _('CBB (Change Requested)')
        DEPRECATED = 'DEPRECATED', _('Deprecated') 
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING_REVIEW,
    )

    # --- CAMPOS DE TRAZABILIDAD (Nivel Sony/Tesis) ---
    review_notes = models.TextField(
        blank=True, 
        null=True,
        help_text="Notas técnicas o artísticas del supervisor."
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions_reviewed',
        help_text="Usuario que realizó la última revisión."
    )
    
    reviewed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Fecha y hora exacta de la decisión."
    )

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

    #approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING_REVIEW)
    transcoding_status = models.CharField(max_length=20, choices=TranscodingStatus.choices, default=TranscodingStatus.PENDING)

    file = models.FileField(_("Original File"), upload_to=get_version_path, max_length=1000) 
    proxy_file_path = models.FileField(max_length=1000, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', max_length=1000, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Version")
        verbose_name_plural = _("Versions")
        unique_together = ('asset', 'version_number', 'department') # Añade 'department' aquí
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
        import hashlib
        
        # 1. QC Original (Aprobación)
        if self.approval_status == self.ApprovalStatus.APPROVED:
            qc_errors = self.check_qc()
            if qc_errors:
                error_msg = _("QC fallido: {errors}").format(errors=', '.join(qc_errors))
                raise ValidationError({'approval_status': error_msg})

        # 2. Bloqueo de Duplicados e Integridad
        if self.file and not self.pk: 
            self.file.seek(0)
            sha256_hash = hashlib.sha256()
            for chunk in self.file.chunks():
                sha256_hash.update(chunk)
            nuevo_hash = sha256_hash.hexdigest()
            self.file.seek(0)

            # Guardamos el hash temporalmente en la instancia para no recalcularlo en el save
            self._temp_hash = nuevo_hash

            # A. VALIDACIÓN GLOBAL (SSOT)
            asset_duplicado = Asset.objects.filter(checksum_sha256=nuevo_hash).exclude(id=self.asset.id).first()
            if asset_duplicado:
                raise ValidationError({'file': _(f"Error: Este archivo ya pertenece al Asset: '{asset_duplicado.name}'.")})

            # B. VALIDACIÓN LOCAL (Redundancia)
            if self.asset.checksum_sha256 == nuevo_hash:
                raise ValidationError({'file': _("Error de Redundancia: Este contenido es idéntico a la versión actual.")})

    def save(self, *args, **kwargs):
        # 1. Si es una versión nueva (no tiene Primary Key)
        if not self.pk:
            # Buscamos la ÚLTIMA instancia física (el objeto) para este asset y depto
            last_instance = self.__class__.objects.filter(
                asset=self.asset, 
                department=self.department
            ).order_by('version_number').last()
            
            # Asignación automática del número si no viene de otro lado
            if self.version_number is None:
                self.version_number = (last_instance.version_number + 1) if last_instance else 1
            
            # AUTOMATIZACIÓN DEL PADRE: 
            # Si existe una instancia previa, se convierte automáticamente en el padre de esta.
            if last_instance:
                self.parent_version = last_instance
            
        # 2. Ejecutamos la validación completa (Aquí es donde truena si el HASH falla)
        self.full_clean()
        
        # 3. Guardado final
        super().save(*args, **kwargs) 
        # --- ÚLTIMO PASO: Actualizar el Asset ---
        # Si calculamos un hash en el clean, lo guardamos en el Asset padre
        if hasattr(self, '_temp_hash'):
            self.asset.checksum_sha256 = self._temp_hash
            self.asset.save()

# --- 6. Comentarios ---
class Comment(models.Model):
    class CommentType(models.TextChoices):
        TECHNICAL = 'TECH', _('Technical Note')
        ARTISTIC = 'ART', _('Artistic Note')
        PIPELINE = 'PIPE', _('Pipeline/Tool Error')
        GENERAL = 'GEN', _('General')

    class Priority(models.IntegerChoices):
        LOW = 1, _('Low')
        NORMAL = 2, _('Normal')
        HIGH = 3, _('High')
        CRITICAL = 4, _('Critical')

    # Relaciones principales
    version = models.ForeignKey(
        'Version', 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='authored_comments'
    )
    
    # Contenido y precisión de VFX
    body = models.TextField(_("Comment Body"))
    frame_number = models.PositiveIntegerField(
        _("Frame"), 
        null=True, 
        blank=True,
        help_text=_("Fotograma específico al que se refiere la nota.")
    )
    
    # Categorización y flujo de trabajo
    type = models.CharField(
        max_length=4, 
        choices=CommentType.choices, 
        default=CommentType.GENERAL
    )
    priority = models.IntegerField(
        choices=Priority.choices, 
        default=Priority.NORMAL
    )
    is_resolved = models.BooleanField(
        default=False,
        help_text=_("Indica si el artista ya atendió esta nota.")
    )
    
    # Jerarquía (Threading)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    
    # Trazabilidad
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")

    def __str__(self):
        frame_info = f" [Fr: {self.frame_number}]" if self.frame_number else ""
        return f"{self.author.username} - {self.get_type_display()}{frame_info}"
    
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