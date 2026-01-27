from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, License, Project, Asset, Version, Comment

# --- 1. Perfiles de Usuario ---
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)

# --- 2. Licencias ---
@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name',)

# --- 3. Proyectos (Con targets de QC) ---
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'target_fps', 'get_target_res', 'created_at')
    search_fields = ('title', 'owner__username')
    
    @admin.display(description='Target Resolution')
    def get_target_res(self, obj):
        return f"{obj.target_width}x{obj.target_height}"

# --- 4. Assets (Con verificación de Hash) ---
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'checksum_sha256', 'created_at')
    list_filter = ('project',)
    search_fields = ('name', 'checksum_sha256')

# --- 5. Versiones (El Cerebro de AXIOM) ---
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
    readonly_fields = ('uuid', 'created_at', 'thumbnail', 'proxy_file_path', 'transcoding_status')
    search_fields = ('asset__name', 'uuid')

    @admin.display(description='Project')
    def get_project(self, obj):
        return obj.asset.project.title

    @admin.display(description='Tech Info (FPS/Res)')
    def get_tech_info(self, obj):
        if obj.fps and obj.resolution_width:
            return f"{obj.fps} fps | {obj.resolution_width}x{obj.resolution_height}"
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
            # Creamos una pequeña vista previa de 100px
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', obj.thumbnail.url)
        return "No Thumb"

# --- 6. Comentarios ---
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'version', 'is_resolved', 'created_at')
    list_filter = ('is_resolved',)
