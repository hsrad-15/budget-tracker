from django.contrib import admin

from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "user"]
    list_filter = ["type"]
    search_fields = ["name"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "amount", "transaction_type", "category", "date"]
    list_filter = ["transaction_type", "category", "date"]
    search_fields = ["title", "description"]
    date_hierarchy = "date"
