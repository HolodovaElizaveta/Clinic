# clinic/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='main'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Запись
    path('book/', views.book_appointment, name='book'),
    path('book/<int:doctor_id>/', views.book_doctor, name='book_doctor'),
    path('appointments/create/<int:doctor_id>/', views.create_appointment, name='create_appointment'),

    # Мои записи
    path('my-appointments/', views.my_appointments, name='my_appointments'),          # для пациента
    path('doctor-appointments/', views.doctor_appointments, name='doctor_appointments'),  # для врача

    # Управление записью
    path('appointment/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointment/<int:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('appointment/<int:appointment_id>/create-history/', views.create_visit_history, name='create_visit_history'),

    # Клиники
    path('clinics/<int:clinic_id>/', views.clinic_detail, name='clinic_detail'),
    path('medical-file/<int:file_id>/', views.download_medical_file, name='download_medical_file'),

     # Админка клиники
    path('admin-appointments/', views.admin_appointments, name='admin_appointments'),
    path('admin/appointment/<int:appointment_id>/update-status/', views.admin_update_appointment_status, name='admin_update_appointment_status'),
]
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)