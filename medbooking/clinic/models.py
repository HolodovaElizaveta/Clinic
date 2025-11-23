# clinic/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

# ====== Choices ======
class UserRole(models.TextChoices):
    PATIENT = 'patient', 'Пациент'
    DOCTOR = 'doctor', 'Врач'
    ADMIN = 'admin', 'Администратор'

class AppointmentStatus(models.TextChoices):
    PLANNED = 'planned', 'Запланирован'
    COMPLETED = 'completed', 'Завершён'
    CANCELLED = 'cancelled', 'Отменён'

class Gender(models.TextChoices):
    MALE = 'male', 'Мужской'
    FEMALE = 'female', 'Женский'


class Clinic(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    photo_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Ссылка на фото клиники (например, фасад здания)"
    )

    def __str__(self):
        return self.name

# ====== Модели ======
class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.PATIENT)
    created_at = models.DateTimeField(auto_now_add=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, blank=True, related_name='admins')  # <-- новое поле
    
   

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    full_name = models.CharField(max_length=255)  
    phone = models.CharField(max_length=20)
    birth_date = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)

    def __str__(self):
        return self.full_name

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    full_name = models.CharField(max_length=255)  
    specialization = models.CharField(max_length=255)
    experience_years = models.PositiveSmallIntegerField()
    bio = models.TextField(blank=True, null=True)
    clinics = models.ManyToManyField(Clinic, related_name='doctors')
    price = models.SmallIntegerField(verbose_name="Цена")
    photo_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Ссылка на фото врача"
    )

    def __str__(self):
        return self.full_name

class Schedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    time = models.TimeField()
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='schedules')
    class Meta:
        unique_together = ('doctor', 'date', 'time')
        verbose_name = 'Расписание'
        verbose_name_plural = 'Расписания'

    def __str__(self):
        return f"{self.doctor.full_name} — {self.date} {self.time}"

class Appointment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    schedule = models.OneToOneField(Schedule, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=AppointmentStatus.choices, default=AppointmentStatus.PLANNED)
    notes = models.TextField(blank=True, null=True)
    reminder_sent = models.BooleanField(default=False)

    @property
    def datetime(self):
        from datetime import datetime
        return datetime.combine(self.schedule.date, self.schedule.time)

    def __str__(self):
        return f"Запись: {self.patient.full_name} к {self.schedule.doctor.full_name} ({self.datetime})"

class VisitHistory(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    diagnosis = models.TextField()
    recommendations = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"История визита от {self.created_at.date()}"

class MedicalFile(models.Model):
    file_path = models.FileField(upload_to='medical_files/')
    upload_time = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_files')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='medical_files')
    def can_view_by(self, user):
        """Проверяет, может ли пользователь просматривать этот файл"""
        if user.is_authenticated:
            if user.role == 'patient' and self.owner == user.patient_profile:
                return True
            if user.role == 'doctor' and self.appointment.schedule.doctor.user == user:
                return True
            if user.is_staff:  # админ всегда может
                return True
        return False

    def __str__(self):
        return f"Заключение — {self.owner.full_name} ({self.upload_time.date()})"