import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError # IMPORTANTE para la seguridad
from .utils import calculate_sha256, asset_version_path

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
    color_space = models.CharField(max_length=100, default='ACEScg') 
    timecode_start = models.CharField(max_length=11, default="00:00:00:00")

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='versions', verbose_name=_("Asset"))
    version_number = models.PositiveIntegerField() 
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING_REVIEW)
    transcoding_status = models.CharField(max_length=20, choices=TranscodingStatus.choices, default=TranscodingStatus.PENDING)

    file = models.FileField(_("Original File"), upload_to=asset_version_path, max_length=500) 
    proxy_file_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Version")
        verbose_name_plural = _("Versions")
        unique_together = ('asset', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.asset.name} - v{self.version_number}"

    # --- Lógica de Negocio y Seguridad ---

    def check_qc(self):
        """Compara la realidad técnica contra los objetivos del proyecto."""
        project = self.asset.project
        errors = []
        if self.fps and self.fps != project.target_fps:
            errors.append(f"FPS: {self.fps} (Esperado: {project.target_fps})")
        if self.resolution_width and (self.resolution_width != project.target_width or 
                                      self.resolution_height != project.target_height):
            errors.append(f"Res: {self.resolution_width}x{self.resolution_height}")
        return errors

    def clean(self):
        """Bloquea la aprobación si el archivo no pasa el QC."""
        if self.approval_status == self.ApprovalStatus.APPROVED:
            qc_errors = self.check_qc()
            if qc_errors:
                raise ValidationError({
                    'approval_status': _(f"No se puede aprobar. Errores de QC: {', '.join(qc_errors)}")
                })

    def save(self, *args, **kwargs):
        """Asegura que las validaciones se ejecuten antes de guardar."""
        self.full_clean()
        super().save(*args, **kwargs)

    def ingest_and_verify(self, file_path):
        """Extrae el ADN y los metadatos del archivo."""
        from .utils import calculate_sha256, get_video_metadata
        
        # 1. Hash (ADN)
        generated_hash = calculate_sha256(file_path)
        self.asset.checksum_sha256 = generated_hash
        self.asset.save()
        
        # 2. Metadatos (Ojos)
        meta = get_video_metadata(file_path)
        if meta:
            self.resolution_width = meta.get('width')
            self.resolution_height = meta.get('height')
            self.fps = meta.get('fps')
            self.color_space = meta.get('color_space', 'ACEScg')
            self.save() # Aquí se dispara la validación y el guardado
            return True
        return False

# --- 6. Comentarios ---
class Comment(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    frame_number = models.PositiveIntegerField(_("Frame"), null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)