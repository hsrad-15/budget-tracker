from django.conf import settings
from django.db import models


class TransactionType(models.TextChoices):
    INCOME = "INCOME", "Income"
    EXPENSE = "EXPENSE", "Expense"


class Category(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
        help_text="Null means a default/global category available to everyone.",
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "type", "user"], name="unique_category_per_user"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Transaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="transactions"
    )
    date = models.DateField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "transaction_type"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.amount} ({self.transaction_type})"

    def save(self, *args, **kwargs):
        # Keep transaction_type in sync with its category's type.
        if self.category_id and not self.transaction_type:
            self.transaction_type = self.category.type
        super().save(*args, **kwargs)
