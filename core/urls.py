from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("transactions/", views.TransactionListView.as_view(), name="transaction_list"),
    path("transactions/add/", views.TransactionCreateView.as_view(), name="transaction_add"),
    path("transactions/<int:pk>/edit/", views.TransactionUpdateView.as_view(), name="transaction_edit"),
    path("transactions/<int:pk>/delete/", views.TransactionDeleteView.as_view(), name="transaction_delete"),
    path("reports/weekly/pdf/", views.download_weekly_pdf, name="download_weekly_pdf"),
    path("reports/monthly/pdf/", views.download_monthly_pdf, name="download_monthly_pdf"),
]
