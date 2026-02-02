from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, License, Project, Asset, Version, Comment

# ==========================================
# --- 1. PARCHE DE JERARQUÍA (EL PSY KONGROO) ---
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
                "License": 6,
            }
            app['models'].sort(key=lambda x: ordering.get(x['object_name'], 99))
    return app_list

admin.AdminSite.get_app_list = get_app_list


# ==========================================
# --- 2. ADMINS DE SOPORTE (PROYECTOS Y ASSETS) ---
# ==========================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'target_fps', 'get_target_res', 'created_at')
    search_fields = ('title', 'owner__username')
    
    @admin.display(description='Target Resolution')
    def get_target_res(self, obj):
        return f"{obj.target_width}x{obj.target_height}"

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'checksum_sha256', 'created_at')
    list_filter = ('project',)
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
        'get_tech_info', 
        'qc_status', 
        'approval_status'
    )
    list_filter = ('approval_status', 'asset__project')
    search_fields = ('asset__name', 'uuid')

    # BLINDAJE TÉCNICO COMPLETO
    readonly_fields = (
        'uuid', 
        'created_at', 
        'thumbnail', 
        'display_proxy', # Link clickable
        'transcoding_status',
        'fps',
        'resolution_width',
        'resolution_height',
        'display_human_duration',
        'filesize',
        'color_space'
    )
    
    # Ocultamos la ruta de texto para que solo se vea el link clickable
    exclude = ('proxy_file_path', 'duration')

    def get_readonly_fields(self, request, obj=None):
        """Bloquea el Approval Status para artistas."""
        if not request.user.is_superuser:
            return self.readonly_fields + ('approval_status',)
        return self.readonly_fields
    
    @admin.display(description='Duration (HH:MM:SS)')
    def display_human_duration(self, obj):
        """Convierte segundos crudos (ej: 787.92) en formato tiempo (00:13:07.92)."""
        if obj.duration:
            hours = int(obj.duration // 3600)
            minutes = int((obj.duration % 3600) // 60)
            seconds = obj.duration % 60
            return f"{hours:02}:{minutes:02}:{seconds:05.2f}"
        return "---"

    # --- FUNCIONES DE VISUALIZACIÓN ---

    @admin.display(description='Project')
    def get_project(self, obj):
        return obj.asset.project.title

    @admin.display(description='Tech Info (FPS/Res/VFX)')
    def get_tech_info(self, obj):
        """Muestra FPS, Res, Espacio de Color, Duración y Peso."""
        if obj.fps and obj.resolution_width:
            # 1. Formateo de Peso
            size_mb = f"{obj.filesize / (1024*1024):.2f} MB" if obj.filesize else "---"
            
            # 2. Formateo de Duración (MM:SS.ss)
            if obj.duration:
                mins = int(obj.duration // 60)
                secs = obj.duration % 60
                dur_str = f"{mins:02}:{secs:05.2f}" # <-- Nombre de variable: dur_str
            else:
                dur_str = "---"
            
            # 3. Retorno de HTML (Asegúrate de usar dur_str aquí abajo)
            return format_html(
                "{} fps | {}x{}<br><small style='color: #888;'>{} | {} | {}</small>",
                obj.fps, 
                obj.resolution_width, 
                obj.resolution_height, 
                obj.color_space, 
                dur_str,  # <-- CORREGIDO: Antes decía 'dur'
                size_mb
            )
        return "Pendiente"

    @admin.display(description='QC Status')
    def qc_status(self, obj):
        errors = obj.check_qc()
        if errors:
            return format_html(
                '<span style="color: #d9534f; font-weight: bold; cursor: help;" title="{}">⚠️ FAIL</span>',
                ", ".join(errors)
            )
        return format_html('<span style="color: #5cb85c; font-weight: bold;">✅ PASS</span>')

    @admin.display(description='Preview')
    def display_thumb(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', obj.thumbnail.url)
        return "No Thumb"
    
    @admin.display(description='Proxy Link')
    def display_proxy(self, obj):
        """Genera el link funcional para el video."""
        if obj.proxy_file_path:
            return format_html(
                '<a href="/media/{}" target="_blank" style="font-weight: bold; color: #ffaa00;">▶️ Abrir Video Proxy</a>', 
                obj.proxy_file_path
            )
        return "No generado"


# --- COMENTARIOS ---
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'version', 'is_resolved', 'created_at')
    list_filter = ('is_resolved',)