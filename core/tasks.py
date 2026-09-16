"""
Celery tasks: automated weekly (Sunday midnight) and monthly (1st, midnight)
PDF report emails. Scheduled via budgetproject/celery.py beat_schedule.
"""
import logging

from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import User
from .utils import (
    compute_period_stats,
    daily_top_category,
    get_previous_week_range,
    get_previous_month_range,
    weekly_grouped_totals,
)

logger = logging.getLogger(__name__)


def _render_pdf(template_name, context):
    from weasyprint import HTML

    html_string = render_to_string(template_name, context)
    return HTML(string=html_string).write_pdf()


def _send_report_email(user, subject, body_template, pdf_bytes, pdf_filename, context):
    body_html = render_to_string(body_template, context)
    email = EmailMessage(
        subject=subject,
        body=body_html,
        to=[user.email],
    )
    email.content_subtype = "html"
    email.attach(pdf_filename, pdf_bytes, "application/pdf")
    email.send(fail_silently=False)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_weekly_report_for_user(self, user_id):
    try:
        user = User.objects.get(pk=user_id)
        start, end = get_previous_week_range()
        stats = compute_period_stats(user, start, end)

        daily_rows = [
            {"day": day, "amount": amount, "top_category": daily_top_category(user, day)}
            for day, amount in stats["daily_totals"].items()
        ]

        context = {
            "user": user,
            "report_title": "Weekly Expense Report",
            "period_label": f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}",
            "stats": stats,
            "daily_rows": daily_rows,
            "generated_at": timezone.now(),
        }
        pdf_bytes = _render_pdf("reports/pdf_weekly.html", context)
        _send_report_email(
            user,
            subject=f"Your Weekly Expense Report ({start.strftime('%d %b')} - {end.strftime('%d %b')})",
            body_template="emails/weekly_email.html",
            pdf_bytes=pdf_bytes,
            pdf_filename=f"weekly_report_{start}_{end}.pdf",
            context=context,
        )
        logger.info("Weekly report sent to %s", user.email)
    except Exception as exc:
        logger.exception("Failed to send weekly report for user_id=%s", user_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_monthly_report_for_user(self, user_id):
    try:
        user = User.objects.get(pk=user_id)
        start, end = get_previous_month_range()
        stats = compute_period_stats(user, start, end)

        daily_rows = [
            {"day": day, "amount": amount, "top_category": daily_top_category(user, day)}
            for day, amount in stats["daily_totals"].items()
        ]
        weekly_totals = weekly_grouped_totals(stats["daily_totals"], start)

        context = {
            "user": user,
            "report_title": "Monthly Expense Report",
            "period_label": start.strftime("%B %Y"),
            "stats": stats,
            "daily_rows": daily_rows,
            "weekly_totals": weekly_totals,
            "generated_at": timezone.now(),
        }
        pdf_bytes = _render_pdf("reports/pdf_monthly.html", context)
        _send_report_email(
            user,
            subject=f"Your Monthly Expense Report ({start.strftime('%B %Y')})",
            body_template="emails/monthly_email.html",
            pdf_bytes=pdf_bytes,
            pdf_filename=f"monthly_report_{start.strftime('%Y_%m')}.pdf",
            context=context,
        )
        logger.info("Monthly report sent to %s", user.email)
    except Exception as exc:
        logger.exception("Failed to send monthly report for user_id=%s", user_id)
        raise self.retry(exc=exc)


@shared_task
def send_weekly_reports():
    """Fan-out task triggered by Celery Beat every Sunday at midnight."""
    for user_id in User.objects.filter(is_active=True).values_list("id", flat=True):
        send_weekly_report_for_user.delay(user_id)


@shared_task
def send_monthly_reports():
    """Fan-out task triggered by Celery Beat on the 1st of every month at midnight."""
    for user_id in User.objects.filter(is_active=True).values_list("id", flat=True):
        send_monthly_report_for_user.delay(user_id)
