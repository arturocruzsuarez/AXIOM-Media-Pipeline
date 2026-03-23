from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Profile, Project, Asset, Version, Comment, SystemHealth

# ==========================================
# --- 1. JERARQUÍA ---
# ==========================================
def get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    if not app_dict:
        return []

    app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())

    for app in app_list:
        if app['app_label'] == 'pipeline':
            ordering = {
                "Project": 1,
                "Asset": 2,
                "Version": 3,
                "Comment": 4,
                "Profile": 5,
                #"License": 6,
                "SystemHealth": 7,
            }
            app['models'].sort(key=lambda x: ordering.get(x['object_name'], 99))
    return app_list

admin.AdminSite.get_app_list = get_app_list

# ==========================================
# --- 2. ADMINS DE SOPORTE ---
# ==========================================

class CommentInline(admin.TabularInline):
    """Permite gestionar el feedback directamente desde la Versión."""
    model = Comment
    extra = 0
    fields = ('author', 'body', 'frame_number', 'type', 'priority', 'is_resolved')
    readonly_fields = ('created_at',)
    classes = ('collapse',) # Lo mantenemos colapsado para no saturar la vista

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)

#@admin.register(License)
#class LicenseAdmin(admin.ModelAdmin):
 #   list_display = ('name',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'target_fps', 'get_target_res', 'created_at')
    search_fields = ('title', 'owner__username')
    
    @admin.display(description='Target Resolution')
    def get_target_res(self, obj):
        return f"{obj.target_width}x{obj.target_height}"

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'category', 'checksum_sha256')
    list_filter = ('project', 'category')
    search_fields = ('name', 'checksum_sha256')

# ==========================================
# --- 3. EL CEREBRO DE AXIOM (VERSION ADMIN) ---
# ==========================================

@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = (
        'display_thumb',
        'get_project', 
        'asset', 
        'version_number', 
        'department', 
        'get_tech_info', 
        'qc_status', 
        'colored_status' # Usamos la versión con colores
    )
    
    list_filter = ('department', 'approval_status', 'asset__project', 'transcoding_status')
    search_fields = ('asset__name', 'uuid', 'version_number')
    
    # Integramos los comentarios en la vista de la Versión
    inlines = [CommentInline]

    # --- ACCIONES MASIVAS PARA SUPERVISORES ---
    actions = ['approve_versions', 'reject_versions', 'mark_as_cbb']

    fieldsets = (
        ('Ingesta de Archivo', {
            'fields': ('file',),
            'description': 'Selecciona el archivo original para iniciar el pipeline de AXIOM.'
        }),
        ('Identificación de Producción', {
            'fields': ('asset', 'department', 'version_number', 'parent_version', 'uploaded_by')
        }),
        ('Ciclo de Revisión y Aprobación', {
            'fields': ('approval_status', 'review_notes', 'reviewed_by', 'reviewed_at'),
            'description': 'Control de estatus artístico y técnico basado en estándares de la industria.'
        }),
        ('Control de Calidad (QC)', {
            'fields': ('transcoding_status', 'display_proxy', 'display_thumb')
        }),
        ('Metadatos Técnicos (Inmutables)', {
            'classes': ('collapse',), 
            'fields': (
                'uuid', 'fps', 'resolution_width', 'resolution_height', 
                'display_human_duration', 'filesize', 'color_space', 
                'timecode_start', 'extra_metadata'
            )
        }),
    )

    readonly_fields = (
        'uuid', 'version_number', 'created_at', 'display_thumb', 
        'display_proxy', 'transcoding_status', 'fps', 'resolution_width', 
        'resolution_height', 'display_human_duration', 'filesize', 
        'color_space', 'timecode_start', 'reviewed_by', 'reviewed_at'
    )
    
    exclude = ('proxy_file_path', 'duration', 'thumbnail')

    def get_readonly_fields(self, request, obj=None):
        # 1. Verificamos si el usuario tiene el rol de 'Supervisor' en su perfil
        is_supervisor = False
        if hasattr(request.user, 'profile'):
            is_supervisor = request.user.profile.role == 'Supervisor'

        # 2. Lógica de permisos:
        # Si NO es superusuario Y tampoco es un Supervisor, bloqueamos el status.
        if not request.user.is_superuser and not is_supervisor:
            # Los artistas pueden subir versiones, pero no aprobarlas.
            return self.readonly_fields + ('approval_status',)

        # 3. Si es Superuser o Supervisor, tiene el campo habilitado para decidir.
        return self.readonly_fields

    # --- MÉTODOS DE ACCIÓN ---
    @admin.action(description="✅ Aprobar versiones seleccionadas")
    def approve_versions(self, request, queryset):
        queryset.update(
            approval_status=Version.ApprovalStatus.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, "Las versiones han sido marcadas como APROBADAS.")

    @admin.action(description="❌ Rechazar versiones seleccionadas")
    def reject_versions(self, request, queryset):
        queryset.update(
            approval_status=Version.ApprovalStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, "Las versiones han sido RECHAZADAS.")

    @admin.action(description="🎨 Marcar como CBB (Cambios solicitados)")
    def mark_as_cbb(self, request, queryset):
        queryset.update(
            approval_status=Version.ApprovalStatus.CBB,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, "Las versiones han sido marcadas como CBB.")

    # --- MÉTODOS DE VISUALIZACIÓN ---
    @admin.display(description='Status')
    def colored_status(self, obj):
        colors = {
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545',
            'CBB': '#ffc107',
            'PENDING_REVIEW': '#17a2b8',
            'DEPRECATED': '#6c757d'
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 10px; border-radius: 10px; font-weight: bold; font-size: 0.85em;">{}</span>',
            colors.get(obj.approval_status, '#6c757d'),
            obj.get_approval_status_display()
        )

    @admin.display(description='Duration (HH:MM:SS)')
    def display_human_duration(self, obj):
        if obj.duration:
            hours = int(obj.duration // 3600)
            minutes = int((obj.duration % 3600) // 60)
            seconds = obj.duration % 60
            return f"{hours:02}:{minutes:02}:{seconds:05.2f}"
        return "---"

    @admin.display(description='Project')
    def get_project(self, obj):
        return obj.asset.project.title

    @admin.display(description='Tech Info (FPS/Res/VFX)')
    def get_tech_info(self, obj):
        if obj.fps or obj.resolution_width:
            size_mb = f"{obj.filesize / (1024*1024):.2f} MB" if obj.filesize else "---"
            dur_str = self.display_human_duration(obj)
            return format_html(
                "{} fps | {}x{}<br><small style='color: #888;'>{} | {} | {}</small>",
                obj.fps or "--", obj.resolution_width or "--", obj.resolution_height or "--", 
                obj.color_space or "SRGB", dur_str, size_mb
            )
        return "Pendiente"

    @admin.display(description='QC Status')
    def qc_status(self, obj):
        errors = obj.check_qc()
        if errors:
            error_string = ", ".join([str(error) for error in errors])
            return format_html('<span style="color: #d9534f; font-weight: bold; cursor: help;" title="{}">⚠️ FAIL</span>', error_string)
        return format_html('<span style="color: #5cb85c; font-weight: bold;">✅ PASS</span>')

    @admin.display(description='Preview')
    def display_thumb(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="width: 80px; height: auto; border-radius: 5px; border: 1px solid #444;" />', obj.thumbnail.url)
        return "No Thumb"
    
    @admin.display(description='Proxy Link')
    def display_proxy(self, obj):
        try:
            # Intentamos acceder a la URL del archivo proxy.
            # Si el archivo existe y el storage responde correctamente, generamos el enlace.
            if obj.proxy_file_path and obj.proxy_file_path.url:
                return format_html(
                    '<a href="{}" target="_blank" style="font-weight: bold; color: #ffaa00;">▶️ Abrir Video Proxy</a>', 
                    obj.proxy_file_path.url
                )
        except (ValueError, AttributeError):
            # Si el campo está vacío, el archivo físico desapareció o hay un error de storage,
            # capturamos la excepción para mantener la estabilidad de la interfaz.
            pass
        
        return "No generado"

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'version', 'type', 'frame_number', 'priority', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'type', 'priority')
    search_fields = ('body', 'author__username', 'version__uuid')

@admin.register(SystemHealth)
class SystemHealthAdmin(admin.ModelAdmin):
    list_display = ('last_diagnostic', 'storage_score', 'database_score', 'ffmpeg_score', 'integrity_score')
    readonly_fields = ('storage_score', 'database_score', 'ffmpeg_score', 'integrity_score', 'last_diagnostic')