# clinic/views.py
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404
from .models import Doctor, Clinic

# clinic/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Doctor, Clinic,User,Patient,AppointmentStatus 

def index(request):
    doctors = Doctor.objects.all()
    clinics = Clinic.objects.all()
    patient = Patient.objects.all()
    specializations = Doctor.objects.values_list('specialization', flat=True).distinct().order_by('specialization')
    return render(request, 'clinic/index.html', {
        'doctors': doctors,
        'clinics': clinics,
        'specializations': specializations,
        'patient' : patient,
    })


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Patient, Gender

def login_view(request):
    if request.method == 'POST':
        if 'login' in request.POST:
            # Вход
            email = request.POST.get('email')
            password = request.POST.get('password')
           
            try:
                user = User.objects.get(email=email)
                print(f"Попытка входа: email={email}, username={user.username}, password = {user.password}")
                auth_user = authenticate(request, username=email, password=password)
                if auth_user:
                    login(request, auth_user)
                    return redirect('main')
                else:
                    messages.error(request, "Неверный пароль.")
            except User.DoesNotExist:
                messages.error(request, "Аккаунта с такой почтой не существует.")

        elif 'register' in request.POST:
            # Регистрация
            full_name = request.POST.get('full_name').strip()
            email = request.POST.get('email').strip()
            phone = request.POST.get('phone').strip()
            birth_date = request.POST.get('birth_date')
            gender = request.POST.get('gender')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

            # Валидация
            errors = []

            if not full_name:
                errors.append("Укажите ФИО.")
            if not email:
                errors.append("Укажите email.")
            if not phone:
                errors.append("Укажите номер телефона.")
            if not birth_date:
                errors.append("Укажите дату рождения.")
            if not gender:
                errors.append("Укажите пол.")
            if password1 != password2:
                errors.append("Пароли не совпадают.")
            if len(password1) < 8:
                errors.append("Пароль должен быть не менее 8 символов.")

            # Проверка уникальности email и телефона
            if User.objects.filter(email=email).exists():
                errors.append("Пользователь с таким email уже зарегистрирован.")
            if Patient.objects.filter(phone=phone).exists():
                errors.append("Пользователь с таким номером телефона уже зарегистрирован.")

            if errors:
                for err in errors:
                    messages.error(request, err)
                # Вернём данные для автозаполнения (без пароля!)
                context = {
                    'reg_full_name': full_name,
                    'reg_email': email,
                    'reg_phone': phone,
                    'reg_birth_date': birth_date,
                    'reg_gender': gender,
                    'show_register': True,
                }
                return render(request, 'clinic/registration/login.html', context)

            # Создание пользователя
            try:
                user = User.objects.create_user(
                    username=email,  # или сгенерировать уникальный username
                    email=email,
                    password=password1,
                    role='patient'
                )
                Patient.objects.create(
                    user=user,
                    full_name=full_name,
                    phone=phone,
                    birth_date=birth_date,
                    gender=gender
                )
                messages.success(request, "Регистрация прошла успешно! Войдите в систему.")
                return redirect('login')
            except Exception as e:
                messages.error(request, "Ошибка при регистрации. Попробуйте позже.")

    return render(request, 'clinic/registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')
def book_appointment(request):
    doctors = Doctor.objects.all()
    return render(request, 'clinic/doctors/list.html', {'doctors': doctors})

def book_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(request, 'clinic/doctors/list.html', {'doctor': doctor}) 

def clinic_detail(request, clinic_id):
    clinic = get_object_or_404(Clinic, id=clinic_id)
    doctors = clinic.doctors.all()  # ← врачи, связанные с этой клиникой
    return render(request, 'clinic/clinics/detail.html', {
        'clinic': clinic,
        'doctors': doctors
    })
# clinic/views.py (добавьте в конец)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Appointment, Schedule, VisitHistory, MedicalFile
from django.utils import timezone
from datetime import datetime

@login_required
def my_appointments(request):
    """Страница 'Мои записи' для пациента"""
    if request.user.role != 'patient':
        return redirect('main')
    patient = request.user.patient_profile
    appointments = patient.appointments.select_related('schedule__doctor', 'schedule__clinic').order_by('-schedule__date')
    return render(request, 'clinic/appointments/my_appointments.html', {'appointments': appointments})

@login_required
def doctor_appointments(request):
    """Страница 'Мои приёмы' для врача"""
    if request.user.role != 'doctor':
        return redirect('main')
    doctor = request.user.doctor_profile
    appointments = Appointment.objects.filter(
        schedule__doctor=doctor
    ).select_related(
        'patient', 'schedule__clinic'
    ).order_by('schedule__date', 'schedule__time')
    return render(request, 'clinic/appointments/doctor_appointments.html', {'appointments': appointments})

@login_required
def create_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    patient = request.user.patient_profile
    clinics = doctor.clinics.all()

    # Получаем все уникальные даты, на которые у врача есть расписание в выбранной клинике
    available_dates = []
    selected_clinic = request.GET.get('clinic') or request.POST.get('clinic_id')
    if selected_clinic:
        available_dates = Schedule.objects.filter(
            doctor=doctor,
            clinic_id=selected_clinic
        ).values_list('date', flat=True).distinct().order_by('date')

    if request.method == 'POST':
        clinic_id = request.POST.get('clinic_id')
        date = request.POST.get('date')
        time = request.POST.get('time')

        if not all([clinic_id, date, time]):
            messages.error(request, "Заполните все поля.")
            return render(request, 'clinic/appointments/create_appointment.html', {
                'doctor': doctor,
                'clinics': clinics,
                'selected_clinic': clinic_id,
                'available_dates': available_dates,
                'selected_date': date,
                'times': [],
            })

        try:
            schedule = Schedule.objects.get(
                doctor=doctor,
                clinic_id=clinic_id,
                date=date,
                time=time
            )
        except Schedule.DoesNotExist:
            messages.error(request, "Выбранное время недоступно.")
            return redirect('create_appointment', doctor_id=doctor_id)

        if Appointment.objects.filter(schedule=schedule).exists():
            messages.error(request, "Это время уже занято.")
            return redirect('create_appointment', doctor_id=doctor_id)

        Appointment.objects.create(
            patient=patient,
            schedule=schedule,
            status=AppointmentStatus.PLANNED
        )
        messages.success(request, "Вы успешно записаны на приём!")
        return redirect('my_appointments')

    # GET-запрос
    selected_date = request.GET.get('date')
    times = []
    if selected_clinic and selected_date:
        occupied_schedules = Appointment.objects.filter(
            schedule__doctor=doctor,
            schedule__clinic_id=selected_clinic,
            schedule__date=selected_date
        ).values_list('schedule_id', flat=True)

        times = Schedule.objects.filter(
            doctor=doctor,
            clinic_id=selected_clinic,
            date=selected_date
        ).exclude(id__in=occupied_schedules).order_by('time')

    return render(request, 'clinic/appointments/create_appointment.html', {
        'doctor': doctor,
        'clinics': clinics,
        'selected_clinic': selected_clinic,
        'available_dates': available_dates,
        'selected_date': selected_date,
        'times': times,
    })

@login_required
def cancel_appointment(request, appointment_id):
    """Пациент отменяет запись"""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__user=request.user)
    appointment.status = AppointmentStatus.CANCELLED
    appointment.save()
    messages.success(request, "Запись отменена.")
    return redirect('my_appointments')

# clinic/views.py

@login_required
def update_appointment_status(request, appointment_id):
    if request.user.role != 'doctor':
        return redirect('main')
    appointment = get_object_or_404(Appointment, id=appointment_id, schedule__doctor__user=request.user)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in [AppointmentStatus.PLANNED, AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            appointment.status = status
            appointment.save()
            messages.success(request, "Статус приёма обновлён.")
        else:
            messages.error(request, "Недопустимый статус.")
    return redirect('doctor_appointments')

# clinic/views.py
import os
from django.conf import settings
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрация шрифта с правильным путём
font_path = os.path.join(settings.BASE_DIR, 'clinic', 'static', 'fonts', 'DejaVuSans.ttf')
try:
    pdfmetrics.registerFont(TTFont('DejaVu', font_path))
    DEFAULT_FONT = 'DejaVu'
except Exception as e:
    print(f"Шрифт не найден: {e}")
    DEFAULT_FONT = 'Helvetica'

@login_required
def create_visit_history(request, appointment_id):
    if request.user.role != 'doctor':
        return redirect('main')
    appointment = get_object_or_404(Appointment, id=appointment_id, schedule__doctor__user=request.user)
    
    if request.method == 'POST':
        diagnosis = request.POST.get('diagnosis', '').strip()
        recommendations = request.POST.get('recommendations', '').strip()
        
        if diagnosis and recommendations:
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            p.setFont(DEFAULT_FONT, 16)
            p.drawString(50, height - 50, "Медицинское заключение")
            p.setFont(DEFAULT_FONT, 12)
            p.drawString(50, height - 80, f"Пациент: {appointment.patient.full_name}")
            p.drawString(50, height - 100, f"Врач: {appointment.schedule.doctor.full_name}")
            p.drawString(50, height - 120, f"Дата: {appointment.schedule.date}")
            p.drawString(50, height - 140, f"Клиника: {appointment.schedule.clinic.name}")

            # Диагноз
            p.drawString(50, height - 170, "Диагноз:")
            p.setFont(DEFAULT_FONT, 10)
            y = height - 190
            for line in diagnosis.splitlines():
                p.drawString(50, y, line)
                y -= 15

            # Рекомендации
            p.drawString(50, y - 20, "Рекомендации:")
            p.setFont(DEFAULT_FONT, 10)
            y -= 40
            for line in recommendations.splitlines():
                p.drawString(50, y, line)
                y -= 15

            p.showPage()
            p.save()

            pdf_file = buffer.getvalue()
            buffer.close()

            from django.core.files.base import ContentFile
            medical_file = MedicalFile(
                owner=appointment.patient,
                appointment=appointment
            )
            
            medical_file.file_path.save(
                f'заключение_{appointment.id}.pdf',
                ContentFile(pdf_file),
                save=True
            )

            appointment.status = AppointmentStatus.COMPLETED
            appointment.save()
            messages.success(request, "Заключение сохранено и PDF создан.")
        else:
            messages.error(request, "Заполните все поля.")
    
    return redirect('doctor_appointments')

@login_required
def download_medical_file(request, file_id):
    medical_file = get_object_or_404(MedicalFile, id=file_id)

    if not medical_file.can_view_by(request.user):
        messages.error(request, "У вас нет доступа к этому файлу.")
        return redirect('main')

    # Отправляем PDF-файл
    return FileResponse(
        medical_file.file_path.open('rb'),
        content_type='application/pdf',
        as_attachment=False,  # inline — открывать в браузере
        filename=f"заключение_{file_id}.pdf"
    )

# clinic/views.py

@login_required
def admin_appointments(request):
    """Страница 'Мои записи' для администратора клиники"""
    if request.user.role != 'admin':
        return redirect('main')

    # Все клиники, где есть хотя бы один врач
    clinics = Clinic.objects.filter(doctors__isnull=False).distinct()

    selected_clinic_id = request.GET.get('clinic')
    appointments = []
    patients = []
    doctors = []

    if selected_clinic_id:
        try:
            selected_clinic = Clinic.objects.get(id=selected_clinic_id)
            # Все приёмы в выбранной клинике
            appointments = Appointment.objects.filter(
                schedule__clinic=selected_clinic
            ).select_related(
                'patient', 'schedule__doctor', 'schedule__clinic'
            ).order_by('-schedule__date', '-schedule__time')

            # Все пациенты и врачи в этой клинике
            patients = Patient.objects.filter(
                appointments__schedule__clinic=selected_clinic
            ).distinct()
            doctors = Doctor.objects.filter(clinics=selected_clinic).distinct()
        except Clinic.DoesNotExist:
            messages.error(request, "Клиника не найдена.")
    else:
        selected_clinic = None

    return render(request, 'clinic/appointments/admin_appointments.html', {
        'clinics': clinics,
        'selected_clinic_id': selected_clinic_id,
        'appointments': appointments,
        'patients': patients,
        'doctors': doctors,
    })


@login_required
def admin_update_appointment_status(request, appointment_id):
    """Админ может обновлять статус любого приёма"""
    if request.user.role != 'admin':
        return redirect('main')
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in [AppointmentStatus.PLANNED, AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            appointment.status = status
            appointment.save()
            messages.success(request, f"Статус приёма обновлён на «{appointment.get_status_display()}».")
        else:
            messages.error(request, "Недопустимый статус.")
    return redirect('admin_appointments')