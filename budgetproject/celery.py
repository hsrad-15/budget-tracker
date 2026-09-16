import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "budgetproject.settings")

app = Celery("budgetproject")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Beat schedule: weekly (Sunday 00:00) and monthly (1st, 00:00) report emails.
app.conf.beat_schedule = {
    "send-weekly-report-every-sunday-midnight": {
        "task": "core.tasks.send_weekly_reports",
        "schedule": crontab(hour=0, minute=0, day_of_week=0),  # 0 = Sunday
    },
    "send-monthly-report-first-of-month-midnight": {
        "task": "core.tasks.send_monthly_reports",
        "schedule": crontab(hour=0, minute=0, day_of_month=1),
    },
}
