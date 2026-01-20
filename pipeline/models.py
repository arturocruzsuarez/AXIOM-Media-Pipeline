from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# --- 1. Perfil de Usuario (Roles) ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='Student') # Student, Professor, Admin
    
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
    # Opcional: Relación con Licencia si se requiere
    license = models.ForeignKey(License, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title

# --- 4. Versión (Atomic Asset) ---
class Version(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING_REVIEW = 'PENDING_REVIEW', _('Pending Review')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        DEPRECATED = 'DEPRECATED', _('Deprecated')  # Rollback logic

    class TranscodingStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        ERROR = 'ERROR', _('Error')

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # --- LINAJE ---
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    # --------------

    approval_status = models.CharField(
        max_length=20, 
        choices=ApprovalStatus.choices, 
        default=ApprovalStatus.PENDING_REVIEW
    )
    transcoding_status = models.CharField(
        max_length=20, 
        choices=TranscodingStatus.choices, 
        default=TranscodingStatus.PENDING
    )

    original_file_path = models.CharField(max_length=500)
    proxy_file_path = models.CharField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.project.title} - v{self.version_number}"

# --- 5. Comentarios (Feedback Loop) ---
class Comment(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.version} by {self.author}"