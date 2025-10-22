# clinic/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views



urlpatterns = [
    path('', views.index, name='main'),
    # Аутентификация
    path('login/', auth_views.LoginView.as_view(template_name='clinic/registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='main'), name='logout'),
    # Запись
    path('book/', views.book_appointment, name='book'),
    path('book/<int:doctor_id>/', views.book_doctor, name='book_doctor'),

    # Клиники
    path('clinics/<int:clinic_id>/', views.clinic_detail, name='clinic_detail'),
]