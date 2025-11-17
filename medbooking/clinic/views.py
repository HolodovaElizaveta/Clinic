# clinic/views.py
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404
from .models import Doctor, Clinic
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password

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

         # Если пользователь — пациент, добавляем уведомления
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
        'patient' : patient,
        'upcoming_appointments_doctor': upcoming_appointments_doctor,
        'upcoming_appointments': upcoming_appointments,
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
            birth_date_str = request.POST.get('birth_date')
            gender = request.POST.get('gender')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

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

            # Проверка возраста (≥18 лет)
            if not errors and birth_date_str:
                try:
                    from datetime import date
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
                # Проверка длины
                if len(password1) < 8:
                    errors.append("Пароль должен содержать не менее 8 символов.")
                # Проверка на цифру
                if not any(c.isdigit() for c in password1):
                    errors.append("Пароль должен содержать хотя бы одну цифру.")
                # Проверка на заглавную букву
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

from datetime import date, timedelta

@login_required
def my_appointments(request):
    """Страница 'Мои записи' для пациента"""
    if request.user.role != 'patient':
        return redirect('main')
    patient = request.user.patient_profile
    appointments = patient.appointments.select_related('schedule__doctor', 'schedule__clinic').order_by('-schedule__date')
     # Уведомления: записи на сегодня и завтра
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    upcoming_appointments = patient.appointments.filter(
        status=AppointmentStatus.PLANNED,
        schedule__date__gte=now.date(),
        schedule__date__lte=tomorrow.date()
    ).select_related('schedule__doctor').order_by('schedule__date', 'schedule__time')[:5]
    patient = request.user.patient_profile
    base_qs = patient.appointments.select_related('schedule__doctor', 'schedule__clinic')

    return render(request, 'clinic/appointments/my_appointments.html', {
        'appointments_planned': base_qs.filter(status=AppointmentStatus.PLANNED).order_by('-schedule__date'),
        'appointments_completed': base_qs.filter(status=AppointmentStatus.COMPLETED).order_by('-schedule__date'),
        'appointments_cancelled': base_qs.filter(status=AppointmentStatus.CANCELLED).order_by('-schedule__date'),
        'appointments': appointments,
        'tomorrow': date.today() + timedelta(days=1),
        'upcoming_appointments': upcoming_appointments,
    })

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

    base_qs = Appointment.objects.filter(
        schedule__doctor=doctor
    ).select_related('patient', 'schedule__clinic', 'schedule__doctor')


    # Уведомления для врача: записи на сегодня и завтра
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    upcoming_appointments_doctor = Appointment.objects.filter(
        schedule__doctor=doctor,
        status=AppointmentStatus.PLANNED,
        schedule__date__gte=now.date(),
        schedule__date__lte=tomorrow.date()
    ).select_related('patient', 'schedule__doctor').order_by('schedule__date', 'schedule__time')[:5]

    return render(request, 'clinic/appointments/doctor_appointments.html', {
        'appointments_planned': base_qs.filter(status=AppointmentStatus.PLANNED).order_by('schedule__date', 'schedule__time'),
        'appointments_completed': base_qs.filter(status=AppointmentStatus.COMPLETED).order_by('-schedule__date', '-schedule__time'),
        'appointments_cancelled': base_qs.filter(status=AppointmentStatus.CANCELLED).order_by('-schedule__date', '-schedule__time'),
        'appointments': appointments,
        'doctor': doctor,
        'upcoming_appointments_doctor': upcoming_appointments_doctor,
    })
@login_required
def create_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    patient = request.user.patient_profile
    clinics = doctor.clinics.all()

    # GET-параметры
    selected_clinic = request.GET.get('clinic') or request.POST.get('clinic_id')
    selected_date_str = request.GET.get('date') or request.POST.get('date')

    # Текущая дата и время (без timezone для простоты, если не используется)
    from datetime import datetime, date, time
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    available_dates = []
    times = []

    # Шаг 1: Загрузка доступных дат (только >= сегодня)
    if selected_clinic:
        available_dates = Schedule.objects.filter(
            doctor=doctor,
            clinic_id=selected_clinic,
            date__gte=today  # ← Только сегодня и будущие даты
        ).values_list('date', flat=True).distinct().order_by('date')

    # Шаг 2: Загрузка доступных времён (только свободные и не прошедшие)
    if selected_clinic and selected_date_str:
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except ValueError:
            selected_date = None

        if selected_date:
            # Определение минимального времени для сегодняшнего дня
            min_time = current_time if selected_date == today else time.min

            # Занятые слоты
            occupied_schedule_ids = Appointment.objects.filter(
                schedule__doctor=doctor,
                schedule__clinic_id=selected_clinic,
                schedule__date=selected_date
            ).values_list('schedule_id', flat=True)

            # Свободные и актуальные слоты
            times = Schedule.objects.filter(
                doctor=doctor,
                clinic_id=selected_clinic,
                date=selected_date,
                time__gt=min_time  # ← Только будущие времена (строго больше)
            ).exclude(id__in=occupied_schedule_ids).order_by('time')

    # POST-обработка
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

# clinic/views.py

from django import forms
from datetime import date

class AddScheduleForm(forms.Form):
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
            # Проверка на уникальность (doctor, date, time, clinic)
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
    """Врач добавляет новый слот в своё расписание"""
    if request.user.role != 'doctor':
        return redirect('main')
    
    doctor = request.user.doctor_profile

    if request.method == 'POST':
        form = AddScheduleForm(doctor, request.POST)
        form.initial['doctor'] = doctor  # для валидации
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

# clinic/views.py

from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta

def send_appointment_reminders():
    """
    Отправляет email-напоминания пациентам за 24 часа до приёма.
    Вызывать раз в час через cron или Celery.
    """
    now = timezone.now()
    # Ищем записи, где приём через 24±0.5 часа (чтобы не пропустить при запуске раз в час)
    upcoming_time = now + timedelta(hours=24)
    time_window_start = upcoming_time - timedelta(minutes=30)
    time_window_end = upcoming_time + timedelta(minutes=30)

    appointments = Appointment.objects.filter(
        status=AppointmentStatus.PLANNED,
        reminder_sent=False,
        schedule__date=time_window_start.date()
    ).select_related('patient', 'schedule__doctor', 'schedule__clinic')

    for appt in appointments:
        # Проверяем точное время (на случай, если дата совпадает, а время — нет)
        appointment_datetime = timezone.make_aware(
            datetime.combine(appt.schedule.date, appt.schedule.time)
        )
        if time_window_start <= appointment_datetime <= time_window_end:
            try:
                send_mail(
                    subject="Напоминание о приёме в MEDCLINIC",
                    message=f"""
Здравствуйте, {appt.patient.full_name}!

Напоминаем, что у вас записан приём:
- Врач: {appt.schedule.doctor.full_name}
- Дата: {appt.schedule.date}
- Время: {appt.schedule.time}
- Клиника: {appt.schedule.clinic.name}
- Адрес: {appt.schedule.clinic.address}

Пожалуйста, не опаздывайте!

С уважением,
Команда MEDCLINIC
                    """.strip(),
                    from_email="info@medclinic.com",
                    recipient_list=[appt.patient.user.email],
                    fail_silently=False,
                )
                appt.reminder_sent = True
                appt.save(update_fields=['reminder_sent'])
                print(f"Напоминание отправлено: {appt.patient.user.email}")
            except Exception as e:
                print(f"Ошибка отправки напоминания для {appt.id}: {e}")


@login_required
def update_profile(request):
    """Редактирование профиля пациента (без email и пароля)"""
    if request.user.role != 'patient':
        return redirect('main')
    
    if request.method == 'POST':
        patient = request.user.patient_profile
        user = request.user

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

        # Проверка возраста ≥18
        if birth_date_str:
            try:
                from datetime import date
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
            # Обновление данных (email НЕ обновляется)
            patient.full_name = full_name
            patient.phone = phone
            patient.birth_date = birth_date_str
            patient.gender = gender
            patient.save()
            messages.success(request, "Данные профиля успешно обновлены!")
    
    return redirect('my_appointments')


@login_required
def change_password(request):
    """Смена пароля с проверкой текущего"""
    if request.user.role != 'patient':
        return redirect('main')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        errors = []

        # Проверка текущего пароля
        if not check_password(current_password, request.user.password):
            errors.append("Текущий пароль введён неверно.")

        # Проверка совпадения
        if new_password1 != new_password2:
            errors.append("Новые пароли не совпадают.")

        # Проверка длины
        if len(new_password1) < 8:
            errors.append("Пароль должен содержать не менее 8 символов.")

        # Проверка на цифру
        if not any(c.isdigit() for c in new_password1):
            errors.append("Пароль должен содержать хотя бы одну цифру.")

        # Проверка на заглавную букву
        if not any(c.isupper() for c in new_password1):
            errors.append("Пароль должен содержать хотя бы одну заглавную букву.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            request.user.set_password(new_password1)
            request.user.save()
            # Обновляем сессию, чтобы не разлогинить
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, "Пароль успешно изменён!")
    
    return redirect('my_appointments')