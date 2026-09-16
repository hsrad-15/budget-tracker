import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import TransactionForm, DateRangeFilterForm
from .models import Transaction, TransactionType
from .utils import (
    compute_period_stats,
    daily_top_category,
    get_current_week_range,
    get_current_month_range,
    get_previous_week_range,
    get_previous_month_range,
    weekly_grouped_totals,
)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@login_required
def dashboard(request):
    user = request.user
    week_start, week_end = get_current_week_range()
    stats = compute_period_stats(user, week_start, week_end)

    # All-time metrics for the top cards (income/expense/net/highest/lowest).
    first_transaction = Transaction.objects.filter(user=user).order_by("date").first()
    all_time_start = first_transaction.date if first_transaction else week_start
    all_time = compute_period_stats(user, all_time_start, timezone.localdate())

    recent_transactions = Transaction.objects.filter(user=user).select_related("category")[:10]

    chart_labels = [d.strftime("%a %d") for d in stats["daily_totals"].keys()]
    chart_values = [float(v) for v in stats["daily_totals"].values()]
    category_labels = list(all_time["category_totals"].keys())
    category_values = [float(v) for v in all_time["category_totals"].values()]

    context = {
        "all_time": all_time,
        "week_stats": stats,
        "recent_transactions": recent_transactions,
        "chart_labels_json": json.dumps(chart_labels),
        "chart_values_json": json.dumps(chart_values, cls=DecimalEncoder),
        "category_labels_json": json.dumps(category_labels),
        "category_values_json": json.dumps(category_values, cls=DecimalEncoder),
    }
    return render(request, "dashboard.html", context)


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = "transactions/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 15

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user).select_related("category")
        self.filter_form = DateRangeFilterForm(self.request.GET or None, user=self.request.user)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("start_date"):
                qs = qs.filter(date__gte=data["start_date"])
            if data.get("end_date"):
                qs = qs.filter(date__lte=data["end_date"])
            if data.get("category"):
                qs = qs.filter(category=data["category"])
            if data.get("transaction_type"):
                qs = qs.filter(transaction_type=data["transaction_type"])
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(title__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["search_query"] = self.request.GET.get("q", "")
        return context


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transaction_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Transaction added successfully.")
        return super().form_valid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transaction_list")

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Transaction updated successfully.")
        return super().form_valid(form)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = "transactions/transaction_confirm_delete.html"
    success_url = reverse_lazy("transaction_list")

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Transaction deleted.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# PDF report downloads (on-demand, triggered from the dashboard buttons)
# ---------------------------------------------------------------------------

def _render_pdf(template_name, context):
    from weasyprint import HTML  # imported lazily so the app still runs without it installed

    html_string = render_to_string(template_name, context)
    pdf_file = HTML(string=html_string).write_pdf()
    return pdf_file


@login_required
def download_weekly_pdf(request):
    user = request.user
    start, end = get_current_week_range()
    stats = compute_period_stats(user, start, end)

    daily_rows = []
    for day, amount in stats["daily_totals"].items():
        daily_rows.append({
            "day": day,
            "amount": amount,
            "top_category": daily_top_category(user, day),
        })

    context = {
        "user": user,
        "report_title": "Weekly Expense Report",
        "period_label": f"{start.strftime('%d %b %Y')} - {end.strftime('%d %b %Y')}",
        "stats": stats,
        "daily_rows": daily_rows,
        "generated_at": timezone.now(),
    }
    pdf_bytes = _render_pdf("reports/pdf_weekly.html", context)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="weekly_report_{start}_{end}.pdf"'
    return response


@login_required
def download_monthly_pdf(request):
    user = request.user
    start, end = get_current_month_range()
    stats = compute_period_stats(user, start, end)

    daily_rows = []
    for day, amount in stats["daily_totals"].items():
        daily_rows.append({
            "day": day,
            "amount": amount,
            "top_category": daily_top_category(user, day),
        })

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
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="monthly_report_{start.strftime("%Y_%m")}.pdf"'
    return response
