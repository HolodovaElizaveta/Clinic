# medbooking/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views  # ← добавьте это
from clinic.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='main'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='main'), name='logout'),  # ← вот он
]

# Только в режиме разработки
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)