# cuajicine_api/urls.py  <-- ¡Fíjate bien en la carpeta!

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views # <-- 1. Importa la vista de tokens

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Aquí conectas tus rutas de pipeline (el archivo que me enseñaste arriba)
    path('api/', include('pipeline.urls')), 
    
    # --- LA TAQUILLA ---
    # 2. Agrega esta línea para que exista la ruta de login
    path('api-token-auth/', views.obtain_auth_token),
]