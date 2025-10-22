# clinic/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    User, Clinic, Patient, Doctor,
    Schedule, Appointment, VisitHistory, MedicalFile
)

# ========== User ==========
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'created_at', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email')}),
        ('Роль и доступ', {'fields': ('role', 'is_staff', 'is_active', 'is_superuser')}),
        ('Важные даты', {'fields': ('last_login', 'created_at')}),
    )
    readonly_fields = ('created_at',)

# ========== Clinic ==========
@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address_preview', 'photo_preview')
    search_fields = ('name', 'address')
    list_per_page = 20

    def address_preview(self, obj):
        return (obj.address[:60] + '...') if len(obj.address) > 60 else obj.address
    address_preview.short_description = 'Адрес'

    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto; border-radius: 4px;" />',
                obj.photo_url
            )
        return "—"
    photo_preview.short_description = 'Фото'

# ========== Patient ==========
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user_email', 'phone', 'birth_date', 'gender')
    list_filter = ('gender', 'birth_date')
    search_fields = ('full_name', 'phone', 'user__email')
    autocomplete_fields = ['user']
    list_per_page = 25

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

# ========== Doctor ==========
@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'specialization', 'experience_years', 'photo_preview', 'clinics_list')
    list_filter = ('specialization', 'clinics', 'experience_years')
    search_fields = ('full_name', 'specialization', 'bio')
    filter_horizontal = ('clinics',)  # удобный виджет для M2M
    autocomplete_fields = ['user']
    list_per_page = 20

    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" style="width: 50px; height: auto; border-radius: 4px;" />',
                obj.photo_url
            )
        return "—"
    photo_preview.short_description = 'Фото'

    def clinics_list(self, obj):
        return ", ".join([c.name for c in obj.clinics.all()[:3]])
    clinics_list.short_description = 'Клиники'

# ========== Schedule ==========
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'clinic', 'date', 'time', 'appointment_status')
    list_filter = ('date', 'clinic', 'doctor__specialization', 'doctor')
    search_fields = ('doctor__full_name', 'clinic__name')
    date_hierarchy = 'date'
    ordering = ('date', 'time')
    list_per_page = 30
    autocomplete_fields = ['doctor', 'clinic']  # ← важно для удобства

    # Валидация: врач должен работать в выбранной клинике
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "clinic":
            if 'object_id' in request.resolver_match.kwargs:
                # Редактирование существующего
                obj = self.get_object(request, request.resolver_match.kwargs['object_id'])
                if obj and obj.doctor_id:
                    kwargs["queryset"] = Clinic.objects.filter(doctors=obj.doctor)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def appointment_status(self, obj):
        try:
            return obj.appointment.get_status_display()
        except:
            return "Свободно"
    appointment_status.short_description = 'Статус записи'

# ========== Appointment ==========
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'clinic', 'datetime_display', 'status', 'has_visit_history', 'has_files')
    list_filter = ('status', 'schedule__date', 'schedule__doctor__specialization', 'schedule__clinic')
    search_fields = ('patient__full_name', 'schedule__doctor__full_name', 'schedule__clinic__name')
    autocomplete_fields = ['patient', 'schedule']
    list_per_page = 25
    readonly_fields = ('datetime_display', 'doctor', 'clinic')

    def datetime_display(self, obj):
        return obj.datetime.strftime('%d.%m.%Y %H:%M')
    datetime_display.short_description = 'Дата и время'

    def doctor(self, obj):
        return obj.schedule.doctor.full_name
    doctor.short_description = 'Врач'

    def clinic(self, obj):
        return obj.schedule.clinic.name
    clinic.short_description = 'Клиника'

    def has_visit_history(self, obj):
        return hasattr(obj, 'visit_history')
    has_visit_history.boolean = True
    has_visit_history.short_description = 'Есть история?'

    def has_files(self, obj):
        return obj.medical_files.exists()
    has_files.boolean = True
    has_files.short_description = 'Есть файлы?'

# ========== VisitHistory ==========
@admin.register(VisitHistory)
class VisitHistoryAdmin(admin.ModelAdmin):
    list_display = ('appointment_info', 'created_at')
    search_fields = (
        'appointment__patient__full_name',
        'appointment__schedule__doctor__full_name',
        'diagnosis'
    )
    autocomplete_fields = ['appointment']
    readonly_fields = ('created_at',)

    def appointment_info(self, obj):
        appt = obj.appointment
        return f"{appt.patient.full_name} → {appt.schedule.doctor.full_name} ({appt.schedule.clinic.name}) — {appt.datetime.strftime('%d.%m.%Y')}"
    appointment_info.short_description = 'Запись'

# ========== MedicalFile ==========
@admin.register(MedicalFile)
class MedicalFileAdmin(admin.ModelAdmin):
    list_display = ('owner', 'appointment_info', 'upload_time', 'file_link')
    list_filter = ('upload_time', 'owner')
    search_fields = ('owner__full_name',)
    autocomplete_fields = ['owner', 'appointment']
    readonly_fields = ('upload_time',)

    def appointment_info(self, obj):
        appt = obj.appointment
        return f"{appt.schedule.doctor.full_name} в {appt.schedule.clinic.name} ({appt.datetime.strftime('%d.%m.%Y')})"
    appointment_info.short_description = 'Приём'

    def file_link(self, obj):
        if obj.file_path:
            return format_html('<a href="{}" target="_blank">📄 Открыть PDF</a>', obj.file_path.url)
        return "—"
    file_link.short_description = 'Файл'