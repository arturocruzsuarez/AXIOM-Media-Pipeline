# pipeline/models.py
from django.db import models
from django.conf import settings

# ... (Aquí va tu clase Profile que ya escribiste) ...
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
    # La "grapa" Muchos-a-Uno con el Pasaporte (User)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Apunta al User
        on_delete=models.CASCADE    # Si borras el User, borra este Project
    )

    # El resto de los campos de tu documento
    title = models.CharField(max_length=255)
    synopsis = models.TextField(blank=True) # blank=True significa que puede estar vacío
    cover_image_path = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        # Para que se vea bonito en el admin
        return f'{self.title} (por {self.owner.username})'
    
    
# Esta es la Tabla 4: Version (El "Corazón" del Pipeline)
class Version(models.Model):
    
    # --- Aquí definimos el "menú" para el estado de aprobación ---
    # Esto traduce tu requerimiento [cite: 1761]
    class ApprovalStatus(models.TextChoices):
        # El formato es: VARIABLE = 'Valor en BBDD', 'Valor legible'
        PENDING = 'PENDING_REVIEW', 'Pendiente de Revisión'
        APPROVED = 'APPROVED', 'Aprobado'
        REJECTED = 'REJECTED', 'Rechazado'

    # --- Y definimos el "menú" para el estado de transcodificación ---
    # Esto traduce tu requerimiento 
    class TranscodingStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        PROCESSING = 'PROCESSING', 'Procesando'
        COMPLETED = 'COMPLETED', 'Completo'
        FAILED = 'FAILED', 'Falló' # Es buena idea tener un estado de error

    # --- Ahora los campos del modelo ---
    
    # La "grapa" que conecta esta Versión a su Proyecto [cite: 1758]
    project = models.ForeignKey(
        Project, # Conecta con la clase Project de arriba
        on_delete=models.CASCADE,
        related_name='versions' # Esto nos permite hacer project.versions
    )
    
    version_number = models.PositiveIntegerField(default=1) # [cite: 1759]
    
    # Campo de Aprobación. ¡Aquí usamos tu idea!
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

    # Las rutas a los archivos en S3/MinIO [cite: 1763, 1764]
    original_file_path = models.CharField(max_length=1024, blank=True)
    proxy_file_path = models.CharField(max_length=1024, blank=True)
    
    # Quién subió esta versión específica [cite: 1760]
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Si se borra el user, no borres la versión
        null=True                  # Permite que el user sea nulo
    )

    def __str__(self):
        return f'{self.project.title} - v{self.version_number} ({self.get_approval_status_display()})'
    
# Esta es la Tabla 5: Comment (El Feedback del Admin)
class Comment(models.Model):
    # La "grapa" que conecta este comentario a su Versión
    version = models.ForeignKey(
        Version, # Conecta con la clase Version
        on_delete=models.CASCADE,
        related_name='comments' # Nos permite hacer version.comments
    )
    
    # Quién escribió el comentario (un Admin)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Si borras al admin, no borres su comentario
        null=True
    )
    
    # El texto del feedback
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True) # Para saber cuándo se hizo

    def __str__(self):
        return f'Comentario de {self.author.username} en {self.version}'


# Esta es la Tabla 6: License (Contenido Comercial)
class License(models.Model):
    # La "grapa" que conecta esta licencia a un Proyecto
    project = models.OneToOneField( # Un proyecto comercial tiene una sola licencia
        Project,
        on_delete=models.CASCADE,
        related_name='license'
    )
    
    provider = models.CharField(max_length=255) # Ej. "Warner Bros" [cite: 313]
    start_date = models.DateField()             # Fecha de inicio
    end_date = models.DateField()               # Fecha de vigencia

    def __str__(self):
        return f'Licencia de {self.project.title} (Vence: {self.end_date})'