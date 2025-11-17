# pipeline/models.py
from django.db import models
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    matricula = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.user.username


# Esta es la Tabla 3: Project (El "Contenido" o "Idea")
class Project(models.Model):
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Apunta al User
        on_delete=models.CASCADE    # Si se borra el User, se borra este Project
    )

    # El resto de los campos del documento
    title = models.CharField(max_length=255)
    synopsis = models.TextField(blank=True) # blank=True significa que puede estar vacío
    cover_image_path = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        # Para que se vea bonito en el admin
        return f'{self.title} (por {self.owner.username})'
    
    
# Esta es la Tabla 4: Version (El "Corazón" del Pipeline)
class Version(models.Model):
    
    # --- Aquí definimos el "menú" para el estado de aprobación ---
    
    class ApprovalStatus(models.TextChoices):
        # El formato es: VARIABLE = 'Valor en BBDD', 'Valor legible'
        PENDING = 'PENDING_REVIEW', 'Pendiente de Revisión'
        APPROVED = 'APPROVED', 'Aprobado'
        REJECTED = 'REJECTED', 'Rechazado'

    # --- Y definimos el "menú" para el estado de transcodificación ---
    
    class TranscodingStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        PROCESSING = 'PROCESSING', 'Procesando'
        COMPLETED = 'COMPLETED', 'Completo'
        FAILED = 'FAILED', 'Falló' # Es buena idea tener un estado de error

    # --- Ahora los campos del modelo ---
    
    # Lo que conecta esta Versión a su Proyecto 
    project = models.ForeignKey(
        Project, # Conecta con la clase Project de arriba
        on_delete=models.CASCADE,
        related_name='versions' # Esto nos permite hacer project.versions
    )
    
    version_number = models.PositiveIntegerField(default=1) 
    
    # Campo de Aprobación. 
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,  # <-- Usa el menú desplegable
        default=ApprovalStatus.PENDING   # <-- Toda nueva versión empieza como "Pendiente"
    )

    # Campo de Transcodificación.
    transcoding_status = models.CharField(
        max_length=20,
        choices=TranscodingStatus.choices, # <-- Usa el otro menú
        default=TranscodingStatus.PENDING
    )

    
    original_file_path = models.CharField(max_length=1024, blank=True)
    proxy_file_path = models.CharField(max_length=1024, blank=True)
    
    # Quién subió esta versión específica 
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True                  # Permite que el user sea nulo
    )

    def __str__(self):
        return f'{self.project.title} - v{self.version_number} ({self.get_approval_status_display()})'
    
# Esta es la Tabla 5: Comment (El Feedback del Admin)
class Comment(models.Model):
    # Lo que conecta este comentario a su Versión
    version = models.ForeignKey(
        Version, # Conecta con la clase Version
        on_delete=models.CASCADE,
        related_name='comments' # Nos permite hacer version.comments
    )
    
    # Quién escribió el comentario (un Admin)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Si se borra al admin, no borres su comentario
        null=True
    )
    
    # El texto del feedback
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True) # Para saber cuándo se hizo

    def __str__(self):
        return f'Comentario de {self.author.username} en {self.version}'


# Esta es la Tabla 6: License (Contenido Comercial)
class License(models.Model):
    # Lo que  conecta esta licencia a un Proyecto
    project = models.OneToOneField( # Un proyecto comercial tiene una sola licencia
        Project,
        on_delete=models.CASCADE,
        related_name='license'
    )
    
    provider = models.CharField(max_length=255) # Ej. "Warner Bros" 
    start_date = models.DateField()             # Fecha de inicio
    end_date = models.DateField()               # Fecha de vigencia

    def __str__(self):
        return f'Licencia de {self.project.title} (Vence: {self.end_date})'