"""
Statistics helpers shared across the dashboard view, PDF report generation,
and the Celery email tasks — single source of truth for how numbers are computed.
"""
from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import Transaction, TransactionType


def _qs_for_range(user, start_date, end_date):
    return Transaction.objects.filter(user=user, date__gte=start_date, date__lte=end_date)


def compute_period_stats(user, start_date, end_date):
    """
    Core metrics for any date range: totals, highest/lowest expense,
    per-day and per-week averages, and category breakdown.
    """
    qs = _qs_for_range(user, start_date, end_date)
    expenses = qs.filter(transaction_type=TransactionType.EXPENSE)
    incomes = qs.filter(transaction_type=TransactionType.INCOME)

    total_income = incomes.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_expense = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    net_balance = total_income - total_expense

    highest_expense = expenses.order_by("-amount").first()
    lowest_expense = expenses.order_by("amount").first()

    num_days = (end_date - start_date).days + 1
    num_weeks = max(Decimal(num_days) / Decimal(7), Decimal("1") / Decimal(7))

    avg_per_day = (total_expense / num_days) if num_days else Decimal("0")
    avg_per_week = (total_expense / num_weeks) if num_weeks else Decimal("0")

    # Category breakdown (for donut chart / PDF)
    category_totals = OrderedDict()
    for tx in expenses.select_related("category"):
        category_totals[tx.category.name] = category_totals.get(tx.category.name, Decimal("0")) + tx.amount

    # Daily breakdown (for bar chart / PDF tabular section)
    daily_totals = OrderedDict()
    current = start_date
    while current <= end_date:
        daily_totals[current] = Decimal("0")
        current += timedelta(days=1)
    for tx in expenses:
        daily_totals[tx.date] = daily_totals.get(tx.date, Decimal("0")) + tx.amount

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "highest_expense": highest_expense,
        "lowest_expense": lowest_expense,
        "avg_per_day": avg_per_day.quantize(Decimal("0.01")),
        "avg_per_week": avg_per_week.quantize(Decimal("0.01")),
        "category_totals": category_totals,
        "daily_totals": daily_totals,
    }


def daily_top_category(user, day):
    """Return the category name with the highest spend on a given day (or None)."""
    row = (
        Transaction.objects.filter(user=user, date=day, transaction_type=TransactionType.EXPENSE)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
        .first()
    )
    return row["category__name"] if row else None


def get_current_week_range(reference_date=None):
    """Monday–Sunday range containing reference_date (defaults to today)."""
    reference_date = reference_date or timezone.localdate()
    start = reference_date - timedelta(days=reference_date.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end


def get_previous_week_range(reference_date=None):
    start, _ = get_current_week_range(reference_date)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)
    return prev_start, prev_end


def get_current_month_range(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    start = reference_date.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    end = next_month - timedelta(days=1)
    return start, end


def get_previous_month_range(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    first_of_this_month = reference_date.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    first_of_prev_month = last_of_prev_month.replace(day=1)
    return first_of_prev_month, last_of_prev_month


def weekly_grouped_totals(daily_totals, month_start):
    """
    Group a dict of {date: Decimal} into Week 1..Week N buckets, anchored
    to the 1st of the month, for the monthly PDF's weekly summary table.
    """
    weeks = OrderedDict()
    for day, amount in daily_totals.items():
        week_index = ((day - month_start).days // 7) + 1
        label = f"Week {week_index}"
        weeks[label] = weeks.get(label, Decimal("0")) + amount
    return weeks
