from django.contrib import admin
from .models import Profile, License, Project, Asset, Version, Comment

# --- Administrador de Proyectos ---
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at')
    search_fields = ('title', 'owner__username')
    list_filter = ('created_at',)

# --- Administrador de Assets (La clave de la deduplicación) ---
class AssetAdmin(admin.ModelAdmin):
    # Mostramos el hash para verificar la integridad visualmente
    list_display = ('name', 'project', 'checksum_sha256', 'created_at')
    search_fields = ('name', 'project__title', 'checksum_sha256')
    list_filter = ('project', 'created_at')

# --- Administrador de Versiones (Siguiendo a MovieLabs) ---
class VersionAdmin(admin.ModelAdmin):
    # Usamos un método para traer el proyecto desde el Asset
    list_display = ('get_project', 'asset', 'version_number', 'approval_status', 'transcoding_status')
    list_filter = ('approval_status', 'transcoding_status', 'asset__project')
    search_fields = ('asset__name', 'uuid')
    
    # Este método "salta" de Version a Asset y de Asset a Project
    @admin.display(description='Project')
    def get_project(self, obj):
        return obj.asset.project.title

# --- Registro de los modelos ---
admin.site.register(Profile)
admin.site.register(License)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Asset, AssetAdmin)
admin.site.register(Version, VersionAdmin)
admin.site.register(Comment)
