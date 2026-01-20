from django.contrib import admin
from .models import Profile, Project, Version, Comment, License

# Configuración opcional para ver mejor los datos en el panel
class VersionAdmin(admin.ModelAdmin):
    list_display = ('project', 'version_number', 'approval_status', 'transcoding_status', 'created_at')
    list_filter = ('approval_status', 'transcoding_status')

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at')

# Registro de modelos
admin.site.register(Profile)
admin.site.register(License)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Version, VersionAdmin)
admin.site.register(Comment)