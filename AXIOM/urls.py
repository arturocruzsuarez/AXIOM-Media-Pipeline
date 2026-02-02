from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas de la lógica de AXIOM
    path('api/', include('pipeline.urls')), 
    
    # --- LA TAQUILLA (Autenticación) ---
    # Esto genera el token para que los scripts externos se conecten
    path('api-token-auth/', views.obtain_auth_token),
    path('pipeline/', include('pipeline.urls')),
]

# Esto permite que AXIOM sirva los videos en modo desarrollo (muy importante para VFX)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)