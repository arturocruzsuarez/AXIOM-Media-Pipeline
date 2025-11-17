from django.contrib import admin
from .models import Profile, Project, Version, Comment, License

# --- Registro de Modelos ---
# Le decimos al admin que cree una interfaz para estos modelos

admin.site.register(Profile)
admin.site.register(Project)
admin.site.register(Version)
admin.site.register(Comment)
admin.site.register(License)