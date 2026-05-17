"""
Views for clinic application.
"""

import os
from datetime import datetime, date, time, timedelta
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import models  
from django.db.models import Q  

from .models import (
    Doctor, Clinic, User, Patient, Appointment, Schedule,
    MedicalFile, AppointmentStatus
)
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta



def index(request):
    """Render main page with doctors, clinics, and appointments."""
    # --- Поиск по врачам ---
    search_query = request.GET.get('doctor_search', '').strip()
    if search_query:
        doctors = Doctor.objects.filter(
            models.Q(full_name__icontains=search_query) |
            models.Q(specialization__icontains=search_query)
        )
    else:
        doctors = Doctor.objects.all()

    clinics = Clinic.objects.all()
    specializations = Doctor.objects.values_list('specialization', flat=True).distinct().order_by('specialization')

    upcoming_appointments_doctor = None
    if request.user.is_authenticated and request.user.role == 'doctor':
        doctor_profile = request.user.doctor_profile
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        upcoming_appointments_doctor = Appointment.objects.filter(
            schedule__doctor=doctor_profile,
            status=AppointmentStatus.PLANNED,
            schedule__date__gte=now.date(),
            schedule__date__lte=tomorrow.date()
        ).select_related('patient', 'schedule__doctor').order_by('schedule__date', 'schedule__time')[:5]

    upcoming_appointments = None
    if request.user.is_authenticated and request.user.role == 'patient':
        patient_profile = request.user.patient_profile
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        upcoming_appointments = patient_profile.appointments.filter(
            status=AppointmentStatus.PLANNED,
            schedule__date__gte=now.date(),
            schedule__date__lte=tomorrow.date()
        ).select_related('schedule__doctor').order_by('schedule__date', 'schedule__time')[:5]

    return render(request, 'clinic/index.html', {
        'doctors': doctors,
        'clinics': clinics,
        'specializations': specializations,
        'upcoming_appointments_doctor': upcoming_appointments_doctor,
        'upcoming_appointments': upcoming_appointments,
        'doctor_search_query': search_query,  
    })


def login_view(request):
    """Handle user login and registration."""
    if request.method == 'POST':
        if 'login' in request.POST:
            # === Ограничение по IP ===
            ip = request.META.get('REMOTE_ADDR')
            cache_key = f"login_attempts_{ip}"
            attempts = cache.get(cache_key, 0)

            if attempts >= 5:
                messages.error(request, "Слишком много неудачных попыток входа. Повторите через 15 минут.")
                return render(request, 'clinic/registration/login.html')

            # === Обычная аутентификация ===
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            try:
                user = User.objects.get(email=email)
                auth_user = authenticate(request, username=email, password=password)
                if auth_user:
                    cache.delete(cache_key)
                    login(request, auth_user)
                    return redirect('main')
                else:
                    cache.set(cache_key, attempts + 1, timeout=900)
                    messages.error(request, "Неверный email или пароль.")
            except User.DoesNotExist:
                cache.set(cache_key, attempts + 1, timeout=900)
                messages.error(request, "Неверный email или пароль.")

        elif 'register' in request.POST:
            full_name = request.POST.get('full_name').strip()
            email = request.POST.get('email').strip()
            phone = request.POST.get('phone').strip()
            birth_date_str = request.POST.get('birth_date')
            gender = request.POST.get('gender')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            
            
            consent_email = request.POST.get('consent_email')  # Вернёт 'on' если отмечено

            errors = []

            # Обязательные поля
            if not full_name:
                errors.append("Укажите ФИО.")
            if not email:
                errors.append("Укажите email.")
            if not phone:
                errors.append("Укажите номер телефона.")
            if not birth_date_str:
                errors.append("Укажите дату рождения.")
            if not gender:
                errors.append("Укажите пол.")
            if not password1 or not password2:
                errors.append("Пароль и подтверждение пароля обязательны.")
            
            # === ПРОВЕРКА СОГЛАСИЯ НА РАССЫЛКУ ===
            if not consent_email:
                errors.append("Необходимо дать согласие на получение уведомлений на email.")

            # Проверка возраста (≥18 лет)
            if not errors and birth_date_str:
                try:
                    birth_date = date.fromisoformat(birth_date_str)
                    today = date.today()
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    if age < 18:
                        errors.append("Регистрация доступна только лицам старше 18 лет.")
                except ValueError:
                    errors.append("Некорректный формат даты рождения.")

            # Проверка паролей
            if password1 != password2:
                errors.append("Пароли не совпадают.")
            elif password1:
                if len(password1) < 8:
                    errors.append("Пароль должен содержать не менее 8 символов.")
                if not any(c.isdigit() for c in password1):
                    errors.append("Пароль должен содержать хотя бы одну цифру.")
                if not any(c.isupper() for c in password1):
                    errors.append("Пароль должен содержать хотя бы одну заглавную букву.")

            # Проверка уникальности email и телефона
            if not errors:
                if User.objects.filter(email=email).exists():
                    errors.append("Пользователь с таким email уже зарегистрирован.")
                if Patient.objects.filter(phone=phone).exists():
                    errors.append("Пользователь с таким номером телефона уже зарегистрирован.")

            if errors:
                for err in errors:
                    messages.error(request, err)
                context = {
                    'reg_full_name': full_name,
                    'reg_email': email,
                    'reg_phone': phone,
                    'reg_birth_date': birth_date_str,
                    'reg_gender': gender,
                    'show_register': True,
                }
                return render(request, 'clinic/registration/login.html', context)

            # Создание пользователя
            try:
                user = User.objects.create_user(
                    username=email,
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
    """Log out the current user."""
    logout(request)
    return redirect('login')


def book_appointment(request):
    """Display list of doctors for booking."""
    doctors = Doctor.objects.all()
    return render(request, 'clinic/doctors/list.html', {'doctors': doctors})


def book_doctor(request, doctor_id):
    """Redirect to doctor list with selected doctor (placeholder)."""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(request, 'clinic/doctors/list.html', {'doctor': doctor})


def clinic_detail(request, clinic_id):
    """Show clinic details and associated doctors."""
    clinic = get_object_or_404(Clinic, id=clinic_id)
    doctors = clinic.doctors.all()
    return render(request, 'clinic/clinics/detail.html', {
        'clinic': clinic,
        'doctors': doctors
    })


@login_required
def my_appointments(request):
    """Page 'My appointments' for patient."""
    if request.user.role != 'patient':
        return redirect('main')
    
    patient = request.user.patient_profile
    now = timezone.now()
    today = now.date()
    current_time = now.time()
    
    base_qs = patient.appointments.select_related('schedule__doctor', 'schedule__clinic')
    
   
    appointments_planned = base_qs.filter(
        status=AppointmentStatus.PLANNED
    ).filter(
        models.Q(schedule__date__gt=today) | 
        models.Q(schedule__date=today, schedule__time__gte=current_time)
    ).order_by('schedule__date', 'schedule__time') 
    
 
    appointments_completed = base_qs.filter(status=AppointmentStatus.COMPLETED).order_by('-schedule__date', '-schedule__time')
    appointments_cancelled = base_qs.filter(status=AppointmentStatus.CANCELLED).order_by('-schedule__date', '-schedule__time')
    
    tomorrow = today + timedelta(days=1)
    upcoming_appointments = patient.appointments.filter(
        status=AppointmentStatus.PLANNED,
        schedule__date__gte=today,
        schedule__date__lte=tomorrow
    ).select_related('schedule__doctor').order_by('schedule__date', 'schedule__time')[:5]
    
    return render(request, 'clinic/appointments/my_appointments.html', {
        'appointments_planned': appointments_planned,
        'appointments_completed': appointments_completed,
        'appointments_cancelled': appointments_cancelled,
        'tomorrow': tomorrow,
        'upcoming_appointments': upcoming_appointments,
    })


@login_required
def doctor_appointments(request):
    """Page 'My appointments' for doctor."""
    if request.user.role != 'doctor':
        return redirect('main')
    
    doctor = request.user.doctor_profile
    now = timezone.now()
    today = now.date()
    current_time = now.time()
    
    
    base_qs = Appointment.objects.filter(
        schedule__doctor=doctor
    ).select_related('patient', 'schedule__clinic', 'schedule__doctor')
    
    
    appointments_planned = base_qs.filter(
        status=AppointmentStatus.PLANNED
    ).filter(
        models.Q(schedule__date__gt=today) | 
        models.Q(schedule__date=today, schedule__time__gte=current_time)
    ).order_by('schedule__date', 'schedule__time') 
    
    
    appointments_completed = base_qs.filter(
        status=AppointmentStatus.COMPLETED
    ).order_by('-schedule__date', '-schedule__time')
    
    appointments_cancelled = base_qs.filter(
        status=AppointmentStatus.CANCELLED
    ).order_by('-schedule__date', '-schedule__time')
    
   
    tomorrow = today + timedelta(days=1)
    upcoming_appointments_doctor = Appointment.objects.filter(
        schedule__doctor=doctor,
        status=AppointmentStatus.PLANNED,
        schedule__date__gte=today,
        schedule__date__lte=tomorrow
    ).select_related('patient', 'schedule__doctor').order_by('schedule__date', 'schedule__time')[:5]
    
   
    future_schedules = doctor.schedules.filter(
        models.Q(date__gt=today) | 
        models.Q(date=today, time__gte=current_time)
    ).select_related('clinic').order_by('date', 'time')
    
    return render(request, 'clinic/appointments/doctor_appointments.html', {
        'appointments_planned': appointments_planned,
        'appointments_completed': appointments_completed,
        'appointments_cancelled': appointments_cancelled,
        'doctor': doctor,
        'upcoming_appointments_doctor': upcoming_appointments_doctor,
        'future_schedules': future_schedules,  # ← новое для фильтрации расписания
    })


@login_required
def create_appointment(request, doctor_id):
    """Create appointment with a doctor."""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    patient = request.user.patient_profile
    clinics = doctor.clinics.all()

    selected_clinic = request.GET.get('clinic') or request.POST.get('clinic_id')
    selected_date_str = request.GET.get('date') or request.POST.get('date')

    now = datetime.now()
    today = now.date()
    current_time = now.time()

    available_dates = []
    times = []

    if selected_clinic:
        available_dates = Schedule.objects.filter(
            doctor=doctor,
            clinic_id=selected_clinic,
            date__gte=today
        ).values_list('date', flat=True).distinct().order_by('date')

    if selected_clinic and selected_date_str:
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except ValueError:
            selected_date = None

        if selected_date:
            min_time = current_time if selected_date == today else time.min

            occupied_schedule_ids = Appointment.objects.filter(
                schedule__doctor=doctor,
                schedule__clinic_id=selected_clinic,
                schedule__date=selected_date
            ).values_list('schedule_id', flat=True)

            times = Schedule.objects.filter(
                doctor=doctor,
                clinic_id=selected_clinic,
                date=selected_date,
                time__gt=min_time
            ).exclude(id__in=occupied_schedule_ids).order_by('time')

    if request.method == 'POST':
        clinic_id = request.POST.get('clinic_id')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')

        if not all([clinic_id, date_str, time_str]):
            messages.error(request, "Заполните все поля.")
        else:
            try:
                schedule = Schedule.objects.get(
                    doctor=doctor,
                    clinic_id=clinic_id,
                    date=date_str,
                    time=time_str
                )
                if Appointment.objects.filter(schedule=schedule).exists():
                    messages.error(request, "Это время уже занято.")
                else:
                    Appointment.objects.create(
                        patient=patient,
                        schedule=schedule,
                        status=AppointmentStatus.PLANNED
                    )
                    messages.success(request, "Вы успешно записаны на приём!")
                    return redirect('my_appointments')
            except Schedule.DoesNotExist:
                messages.error(request, "Выбранное время недоступно.")

    return render(request, 'clinic/appointments/create_appointment.html', {
        'doctor': doctor,
        'clinics': clinics,
        'selected_clinic': selected_clinic,
        'available_dates': available_dates,
        'selected_date': selected_date_str,
        'times': times,
    })


@login_required
def cancel_appointment(request, appointment_id):
    """Patient cancels appointment."""
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__user=request.user)
    appointment.status = AppointmentStatus.CANCELLED
    appointment.save()
    messages.success(request, "Запись отменена.")
    return redirect('my_appointments')


@login_required
def update_appointment_status(request, appointment_id):
    """Doctor updates appointment status."""
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


# Font registration
font_path = os.path.join(settings.BASE_DIR, 'clinic', 'static', 'fonts', 'DejaVuSans.ttf')
try:
    pdfmetrics.registerFont(TTFont('DejaVu', font_path))
    DEFAULT_FONT = 'DejaVu'
except Exception as e:
    print(f"Шрифт не найден: {e}")
    DEFAULT_FONT = 'Helvetica'


@login_required
def create_visit_history(request, appointment_id):
    """Generate PDF medical conclusion."""
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

            try:
                pdfmetrics.registerFont(TTFont('DejaVu', font_path))
                font_normal = 'DejaVu'
            except:
                font_normal = 'Helvetica'

            p.setStrokeColorRGB(0.8, 0.8, 0.8)
            p.setLineWidth(0.5)
            p.rect(20, 20, width - 40, height - 40)

            p.setFont(font_normal, 14)
            p.setFillColorRGB(0, 0, 0)
            p.drawCentredString(width / 2, height - 50, "МЕДИЦИНСКИЙ ЦЕНТР «MEDCLINIC»")
            p.setFont(font_normal, 10)
            p.drawCentredString(width / 2, height - 70, "Лицензия № ЛО-77-01-023456 от 15.03.2020")
            p.drawCentredString(width / 2, height - 85, "г. Москва, ул. Здоровья, д. 15")

            p.setFont(font_normal, 16)
            p.drawCentredString(width / 2, height - 120, "МЕДИЦИНСКОЕ ЗАКЛЮЧЕНИЕ")

            y = height - 150
            p.setFont(font_normal, 11)
            p.drawString(50, y, f"Пациент: {appointment.patient.full_name}")
            y -= 20
            p.drawString(50, y, f"Дата рождения: {appointment.patient.birth_date.strftime('%d.%m.%Y')}")
            y -= 20
            p.drawString(50, y, f"Врач: {appointment.schedule.doctor.full_name}")
            y -= 20
            p.drawString(50, y, f"Специализация: {appointment.schedule.doctor.specialization}")
            y -= 20
            p.drawString(50, y, f"Дата приёма: {appointment.schedule.date.strftime('%d.%m.%Y')}")
            y -= 20
            p.drawString(50, y, f"Время приёма: {appointment.schedule.time.strftime('%H:%M')}")
            y -= 20
            p.drawString(50, y, f"Клиника: {appointment.schedule.clinic.name}")
            y -= 30

            p.setFont(font_normal, 12)
            p.setFillColorRGB(0, 0, 0)
            p.drawString(50, y, "Диагноз:")
            y -= 20
            p.setFont(font_normal, 11)
            for line in diagnosis.splitlines():
                p.drawString(70, y, line)
                y -= 16
            y -= 10

            p.setFont(font_normal, 12)
            p.drawString(50, y, "Рекомендации:")
            y -= 20
            p.setFont(font_normal, 11)
            for line in recommendations.splitlines():
                p.drawString(70, y, line)
                y -= 16

            y = 130
            p.setFont(font_normal, 11)
            p.drawString(50, y, f"Врач: ____________________ / {appointment.schedule.doctor.full_name}/")
            y -= 25
            p.drawString(50, y, "Печать медицинского учреждения:")
            p.setStrokeColorRGB(0.7, 0.7, 0.7)
            p.setFillColorRGB(1, 1, 1)
            p.circle(400, y - 5, 25, stroke=1, fill=1)
            p.setFillColorRGB(0.7, 0.7, 0.7)
            p.setFont(font_normal, 8)
            p.drawCentredString(400, y - 8, "MEDCLINIC")
            p.drawCentredString(400, y - 18, "г. Москва")

            p.setFont(font_normal, 8)
            p.setFillColorRGB(0.5, 0.5, 0.5)
            p.drawString(50, 30, "Документ сформирован автоматически. Подпись и печать проставляются при печати.")
            p.drawRightString(width - 50, 30, f"ID заключения: {appointment.id}")

            p.showPage()
            p.save()

            pdf_file = buffer.getvalue()
            buffer.close()

            medical_file = MedicalFile(
                owner=appointment.patient,
                appointment=appointment
            )
            medical_file.file_path.save(
        f'zaklyuchenie_{appointment.id}.pdf',
        ContentFile(pdf_file),
        save=True
    )
    
    # 📩 ОТПРАВКА ЗАКЛЮЧЕНИЯ НА ПОЧТУ ПАЦИЕНТУ
    try:
        email = EmailMessage(
            subject="Медицинское заключение — MEDCLINIC",
            body=(
                f"Здравствуйте, {appointment.patient.full_name}!\n\n"
                f"Ваш приём завершён. Во вложении вы найдёте медицинское заключение.\n\n"
                f"С уважением, команда MEDCLINIC"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[appointment.patient.user.email],
        )
        # Прикрепляем PDF из переменной pdf_file (она уже есть в коде)
        email.attach('zaklyuchenie.pdf', pdf_file, 'application/pdf')
        email.send()
        print(f"✅ Заключение отправлено на почту: {appointment.patient.user.email}")
    except Exception as e:
        print(f"❌ Ошибка отправки заключения: {e}")
    
    # Меняем статус приёма
    appointment.status = AppointmentStatus.COMPLETED
    appointment.save()
    messages.success(request, "Заключение успешно создано, сохранено и отправлено на почту пациента.")
    return redirect('doctor_appointments')


@login_required
def download_medical_file(request, file_id):
    """Download medical file if allowed."""
    medical_file = get_object_or_404(MedicalFile, id=file_id)

    if not medical_file.can_view_by(request.user):
        messages.error(request, "У вас нет доступа к этому файлу.")
        return redirect('main')

    return FileResponse(
        medical_file.file_path.open('rb'),
        content_type='application/pdf',
        as_attachment=False,
        filename=f"заключение_{file_id}.pdf"
    )


@login_required
def admin_appointments(request):
    """Admin view for clinic appointments with doctor/patient search and clinic-bound access."""
    if request.user.role != 'admin':
        return redirect('main')

    # Определяем доступные клиники
    if hasattr(request.user, 'clinic') and request.user.clinic:
        # Админ привязан к клинике — работает только с ней
        clinics = [request.user.clinic]
        selected_clinic = request.user.clinic
        selected_clinic_id = str(selected_clinic.id)
    else:
        # Админ без привязки — может выбирать
        clinics = Clinic.objects.filter(doctors__isnull=False).distinct()
        selected_clinic_id = request.GET.get('clinic')
        selected_clinic = None
        if selected_clinic_id:
            try:
                selected_clinic = Clinic.objects.get(id=selected_clinic_id)
            except Clinic.DoesNotExist:
                messages.error(request, "Клиника не найдена.")

    selected_date_str = request.GET.get('date')
    search_query = request.GET.get('search', '').strip()
    selected_date = None

    appointments = []
    patients = []
    doctors = []
    schedules = []

    if selected_clinic:
        # Фильтрация по дате
        if selected_date_str:
            try:
                selected_date = date.fromisoformat(selected_date_str)
            except ValueError:
                pass

        # Получаем врачей и пациентов
        doctors = Doctor.objects.filter(clinics=selected_clinic).distinct()
        patients = Patient.objects.filter(
            appointments__schedule__clinic=selected_clinic
        ).distinct()

        # Получаем приёмы с опциональным поиском
        appt_qs = Appointment.objects.filter(schedule__clinic=selected_clinic).select_related(
            'patient', 'schedule__doctor', 'schedule__clinic'
        )

        if search_query:
            from django.db.models import Q
            appt_qs = appt_qs.filter(
                Q(patient__full_name__icontains=search_query) |
                Q(schedule__doctor__full_name__icontains=search_query) |
                Q(patient__phone__icontains=search_query)
            )

        appointments = appt_qs.order_by('-schedule__date', '-schedule__time')

        # Получаем расписание с предзагрузкой приёмов
        schedule_qs = Schedule.objects.filter(clinic=selected_clinic).select_related('doctor', 'appointment')
        if selected_date:
            schedule_qs = schedule_qs.filter(date=selected_date)
        schedule_qs = schedule_qs.order_by('doctor', 'date', 'time')

        # Группировка по врачам
        from collections import defaultdict
        schedules_by_doctor = defaultdict(list)
        for slot in schedule_qs:
            schedules_by_doctor[slot.doctor].append(slot)
        schedules = schedules_by_doctor.items()

    context = {
        'clinics': clinics,
        'selected_clinic_id': selected_clinic_id,
        'selected_date': selected_date_str,
        'search_query': search_query,
        'appointments': appointments,
        'patients': patients,
        'doctors': doctors,
        'schedules': schedules,
    }

    return render(request, 'clinic/appointments/admin_appointments.html', context)


@login_required
def admin_update_appointment_status(request, appointment_id):
    """Admin updates any appointment status."""
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


from django import forms


class AddScheduleForm(forms.Form):
    """Form for doctor to add schedule slot."""
    clinic = forms.ModelChoiceField(
        queryset=Clinic.objects.none(),
        label="Клиника",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date = forms.DateField(
        label="Дата",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=date.today
    )
    time = forms.TimeField(
        label="Время",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )

    def __init__(self, doctor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clinic'].queryset = doctor.clinics.all()

    def clean(self):
        cleaned_data = super().clean()
        clinic = cleaned_data.get('clinic')
        date_val = cleaned_data.get('date')
        time_val = cleaned_data.get('time')

        if clinic and date_val and time_val:
            if Schedule.objects.filter(
                doctor=self.initial.get('doctor'),
                clinic=clinic,
                date=date_val,
                time=time_val
            ).exists():
                raise forms.ValidationError("Такой слот уже существует.")
        return cleaned_data


@login_required
def add_doctor_schedule(request):
    """Doctor adds a new schedule slot."""
    if request.user.role != 'doctor':
        return redirect('main')
    
    doctor = request.user.doctor_profile

    if request.method == 'POST':
        form = AddScheduleForm(doctor, request.POST)
        form.initial['doctor'] = doctor
        if form.is_valid():
            Schedule.objects.create(
                doctor=doctor,
                clinic=form.cleaned_data['clinic'],
                date=form.cleaned_data['date'],
                time=form.cleaned_data['time']
            )
            messages.success(request, "Новый слот добавлен в расписание!")
            return redirect('doctor_appointments')
        else:
            messages.error(request, "Исправьте ошибки в форме.")
    else:
        form = AddScheduleForm(doctor)
        form.initial['doctor'] = doctor

    return render(request, 'clinic/appointments/add_schedule.html', {'form': form})


from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.utils import timezone
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz  # ← Импортируем pytz

def send_appointment_reminders():
    """
    Отправляет напоминания за ~24 часа до приёма + .ics для календаря.
    """
    from datetime import datetime, timedelta
    from django.utils import timezone
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    
    now = timezone.now()
    
    # Ищем приёмы в диапазоне 18-30 часов от текущего момента
    target_from = now + timedelta(hours=18)
    target_to = now + timedelta(hours=30)
    
    appointments = Appointment.objects.filter(
        status=AppointmentStatus.PLANNED,
        reminder_sent=False
    ).select_related('patient__user', 'schedule__doctor', 'schedule__clinic')
    
    sent_count = 0
    print(f"⏰ Сейчас (MSK): {timezone.localtime(now)}")
    print(f"🔍 Ищем приёмы в диапазоне: {timezone.localtime(target_from)} — {timezone.localtime(target_to)}")
    print(f"📋 Кандидатов в БД: {appointments.count()}")
    
    # Месяцы на русском
    MONTHS_RU = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    
    for appt in appointments:
        # Создаём datetime из даты и времени
        naive_dt = datetime.combine(appt.schedule.date, appt.schedule.time)
        # Делаем timezone-aware с московским временем (UTC+3)
        appt_dt = timezone.make_aware(naive_dt, timezone.get_fixed_timezone(180))
        
        print(f"📅 Проверка: {appt.patient.user.email} → {appt_dt} (MSK)")
        
        if target_from <= appt_dt <= target_to:
            try:
                # === ФОРМАТИРОВАНИЕ ДАТЫ ===
                day = appt.schedule.date.day
                month = MONTHS_RU[appt.schedule.date.month]
                year = appt.schedule.date.year
                formatted_date = f"{day} {month} {year} года"
                formatted_time = appt.schedule.time.strftime('%H:%M')
                
                # Время окончания (через 1 час)
                end_time = (datetime.combine(appt.schedule.date, appt.schedule.time) + timedelta(hours=1)).time()
                formatted_end_time = end_time.strftime('%H:%M')
                
                # === ССЫЛКА НА ЯНДЕКС.КАРТЫ ===
                clinic_name_encoded = appt.schedule.clinic.name.replace(' ', '+')
                clinic_address_encoded = appt.schedule.clinic.address.replace(' ', '+')
                yandex_maps_url = f"https://yandex.ru/maps/?text={clinic_name_encoded}+{clinic_address_encoded}"
                
                # === ГЕНЕРАЦИЯ .ics ФАЙЛА ВРУЧНУЮ ===
                # Форматируем время для .ics (YYYYMMDDTHHMMSS) — БЕЗ часового пояса!
                dt_start = appt.schedule.date.strftime('%Y%m%d') + 'T' + appt.schedule.time.strftime('%H%M%S')
                dt_end = appt.schedule.date.strftime('%Y%m%d') + 'T' + end_time.strftime('%H%M%S')
                
                # ВАЖНО: без отступов в начале строк и БЕЗ METHOD:REQUEST!
                ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MEDCLINIC//Appointment Reminder//RU
CALSCALE:GREGORIAN
BEGIN:VEVENT
DTSTART:{dt_start}
DTEND:{dt_end}
DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}
UID:appointment-{appt.id}@medclinic.ru
SUMMARY:Приём: {appt.schedule.doctor.full_name} — MEDCLINIC
DESCRIPTION:Пациент: {appt.patient.full_name}\\nВрач: {appt.schedule.doctor.full_name} ({appt.schedule.doctor.specialization})\\nКлиника: {appt.schedule.clinic.name}\\nТелефон: {appt.schedule.clinic.phone}\\nВремя приёма: {formatted_time} (МСК)
LOCATION:{appt.schedule.clinic.address}
STATUS:CONFIRMED
SEQUENCE:0
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""
                
                # 🔍 Отладка: выводим .ics в консоль
                print(f"📎 .ics файл:\n{ics_content}")
                
                # === HTML-ШАБЛОН ПИСЬМА ===
                html_message = f"""
                <!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Напоминание о приёме</title>
                </head>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f6f8;">
                    <div style="max-width: 600px; margin: 20px auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                        <div style="background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 24px 20px; text-align: center;">
                            <h1 style="margin: 0; font-size: 22px; font-weight: 700;">🏥 MEDCLINIC</h1>
                            <p style="margin: 8px 0 0; opacity: 0.95; font-size: 14px;">Напоминание о предстоящем приёме</p>
                        </div>
                        <div style="padding: 24px 20px;">
                            <p style="font-size: 16px; margin-bottom: 20px;">Здравствуйте, <strong>{appt.patient.full_name}</strong>!</p>
                            <p>Напоминаем, что у вас запланирован приём:</p>
                            
                            <div style="background: #f8f9fa; border-left: 4px solid #007bff; border-radius: 8px; padding: 16px; margin: 20px 0;">
                                <h3 style="margin: 0 0 12px; color: #007bff; font-size: 18px;">📋 Детали записи</h3>
                                <p style="margin: 8px 0;"><strong>👨‍️ Врач:</strong> {appt.schedule.doctor.full_name}<br>
                                <small style="color:#666">{appt.schedule.doctor.specialization}</small></p>
                                <p style="margin: 8px 0;"><strong>📅 Дата:</strong> {formatted_date}</p>
                                <p style="margin: 8px 0;"><strong>⏰ Время:</strong> {formatted_time} – {formatted_end_time} <small style="color:#999">(МСК)</small></p>
                                <p style="margin: 8px 0;"><strong>🏥 Клиника:</strong> {appt.schedule.clinic.name}</p>
                                <p style="margin: 8px 0;"><strong>📍 Адрес:</strong> {appt.schedule.clinic.address}</p>
                                <p style="margin: 8px 0;"><strong>📞 Телефон:</strong> {appt.schedule.clinic.phone}</p>
                            </div>
                            
                            <div style="margin: 24px 0; text-align: center;">
                                <a href="{yandex_maps_url}" style="display: inline-block; padding: 12px 24px; margin: 6px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; background: #007bff; color: white;">🗺️ Построить маршрут</a>
                                <p style="display:block; margin:12px 0; font-size:13px; color:#666">📎 Файл для добавления в календарь прикреплён к письму</p>
                            </div>
                            
                            <div style="background:#fff3cd; border:1px solid #ffc107; border-radius:6px; padding:12px; font-size:14px;">
                                <strong>💡 Совет:</strong> Пожалуйста, приходите за 10–15 минут до начала приёма. Не забудьте паспорт и полис.
                            </div>
                        </div>
                        <div style="background: #f8f9fa; padding: 16px 20px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #eee;">
                            <p>С уважением,<br><strong>Команда медицинского центра MEDCLINIC</strong></p>
                            <p style="margin:8px 0 0;">
                                <a href="tel:+78005553535" style="color: #007bff; text-decoration: none;">📞 +7 (800) 555-35-35</a> • 
                                <a href="mailto:m3dclinick@ya.ru" style="color: #007bff; text-decoration: none;">✉️ m3dclinick@ya.ru</a>
                            </p>
                            <p style="margin:12px 0 0; font-size:11px; color:#999;">
                                Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # === ТЕКСТОВАЯ ВЕРСИЯ ===
                text_message = (
                    f"Здравствуйте, {appt.patient.full_name}!\n\n"
                    f"Напоминаем о вашей записи в медицинский центр MEDCLINIC:\n\n"
                    f"👨‍⚕️ Врач: {appt.schedule.doctor.full_name}\n"
                    f"   Специализация: {appt.schedule.doctor.specialization}\n\n"
                    f"📅 Дата: {formatted_date}\n"
                    f"⏰ Время: {formatted_time} – {formatted_end_time} (МСК)\n\n"
                    f"🏥 Клиника: {appt.schedule.clinic.name}\n"
                    f"📍 Адрес: {appt.schedule.clinic.address}\n"
                    f"📞 Телефон: {appt.schedule.clinic.phone}\n\n"
                    f"Построить маршрут:\n{yandex_maps_url}\n\n"
                    f"📎 Файл для добавления в календарь прикреплён к письму.\n\n"
                    f"💡 Пожалуйста, приходите за 10–15 минут до начала приёма.\n"
                    f"   Не забудьте паспорт и полис.\n\n"
                    f"С уважением,\n"
                    f"Команда медицинского центра MEDCLINIC\n"
                    f"📞 +7 (800) 555-35-35\n"
                    f"✉️ m3dclinick@ya.ru"
                )
                
                # === ОТПРАВКА ПИСЬМА ===
                email = EmailMultiAlternatives(
                    subject=f"🏥 Напоминание о приёме {formatted_date} в {formatted_time}",
                    body=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[appt.patient.user.email],
                )
                email.attach_alternative(html_message, "text/html")
                email.attach(f'priem_{appt.id}.ics', ics_content.encode('utf-8'), 'text/calendar')
                email.send()
                
                appt.reminder_sent = True
                appt.save(update_fields=['reminder_sent'])
                sent_count += 1
                print(f"✅ Отправлено: {appt.patient.user.email}")
                
            except Exception as e:
                print(f"❌ Ошибка для {appt.id}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"📬 Итого отправлено: {sent_count}")


@login_required
def update_profile(request):
    """Update patient profile (excluding email)."""
    if request.user.role != 'patient':
        return redirect('main')
    
    if request.method == 'POST':
        patient = request.user.patient_profile
        full_name = request.POST.get('full_name').strip()
        phone = request.POST.get('phone').strip()
        birth_date_str = request.POST.get('birth_date')
        gender = request.POST.get('gender')

        errors = []

        if not full_name:
            errors.append("Укажите ФИО.")
        if not phone:
            errors.append("Укажите номер телефона.")
        if not birth_date_str:
            errors.append("Укажите дату рождения.")
        if not gender:
            errors.append("Укажите пол.")

        if birth_date_str:
            try:
                birth_date = date.fromisoformat(birth_date_str)
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                if age < 18:
                    errors.append("Возраст должен быть 18 лет или старше.")
            except ValueError:
                errors.append("Некорректный формат даты рождения.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            patient.full_name = full_name
            patient.phone = phone
            patient.birth_date = birth_date
            patient.gender = gender
            patient.save()
            messages.success(request, "Данные профиля успешно обновлены!")
    
    return redirect('my_appointments')


@login_required
def change_password(request):
    """Change password with current password verification."""
    if request.user.role != 'patient':
        return redirect('main')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        errors = []

        if not check_password(current_password, request.user.password):
            errors.append("Текущий пароль введён неверно.")
        if new_password1 != new_password2:
            errors.append("Новые пароли не совпадают.")
        if len(new_password1) < 8:
            errors.append("Пароль должен содержать не менее 8 символов.")
        if not any(c.isdigit() for c in new_password1):
            errors.append("Пароль должен содержать хотя бы одну цифру.")
        if not any(c.isupper() for c in new_password1):
            errors.append("Пароль должен содержать хотя бы одну заглавную букву.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            request.user.set_password(new_password1)
            request.user.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, "Пароль успешно изменён!")
    
    return redirect('my_appointments')