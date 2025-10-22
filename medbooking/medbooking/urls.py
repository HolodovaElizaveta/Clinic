# medbooking/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from clinic.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('clinic.urls')),   # все маршруты в clinic.urls
]

# Статика и медиа (только в DEBUG)
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)