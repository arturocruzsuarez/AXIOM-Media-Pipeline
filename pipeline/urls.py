# pipeline/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

# 1. Creamos el Router
router = DefaultRouter()

# 2. Registramos nuestro "Gerente"
# Esto le dice: "Cuando alguien entre a /projects, atiende con ProjectViewSet"
router.register(r'projects', ProjectViewSet)

# 3. Definimos las URLs de la app
urlpatterns = [
    path('', include(router.urls)), # Incluye todas las rutas mágicas del router
]