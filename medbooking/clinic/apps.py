from django.apps import AppConfig
import sys

class ClinicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clinic'
    
    def ready(self):
        # Защита от двойного запуска при auto-reload Django
        if 'runserver' not in sys.argv:
            return
            
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from clinic.views import send_appointment_reminders
            import atexit
            
            # Создаём планировщик
            scheduler = BackgroundScheduler()
            
            # Добавляем задачу: проверять напоминания каждые 30 минут
            scheduler.add_job(
                func=send_appointment_reminders,
                trigger=IntervalTrigger(minutes=2),  # ← можно изменить на hours=1
                id='send_appointment_reminders_job',
                name='Отправка напоминаний о приёмах',
                replace_existing=True,
                max_instances=1,  # запрещает параллельные запуски
                misfire_grace_time=600  # допускает задержку до 10 минут
            )
            
            # Запускаем планировщик
            scheduler.start()
            print("✅ APScheduler запущен: напоминания будут проверяться каждые 2 минут")
            
            # Корректное завершение при остановке сервера
            atexit.register(lambda: scheduler.shutdown(wait=False))
            
        except ImportError:
            print("⚠️  APScheduler не установлен. Выполните: pip install apscheduler")
        except Exception as e:
            print(f"❌ Ошибка запуска APScheduler: {e}")