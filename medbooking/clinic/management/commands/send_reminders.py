# clinic/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from clinic.views import send_appointment_reminders

class Command(BaseCommand):
    help = 'Отправляет напоминания о приёмах за 24 часа'

    def handle(self, *args, **options):
        self.stdout.write('Проверка напоминаний...')
        send_appointment_reminders()
        self.stdout.write(self.style.SUCCESS('Готово.'))