from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Importamos todas las vistas
from .views import ProjectViewSet, VersionViewSet, CommentViewSet, LicenseViewSet

router = DefaultRouter()

# Registramos las rutas
router.register(r'projects', ProjectViewSet)
router.register(r'versions', VersionViewSet)   # <-- Nuevo
router.register(r'comments', CommentViewSet)   # <-- Nuevo
router.register(r'licenses', LicenseViewSet)   # <-- Nuevo

urlpatterns = [
    path('', include(router.urls)),
]