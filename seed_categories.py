"""
Run once after migrating: python manage.py shell < seed_categories.py
Creates a starter set of global categories (user=None) available to every user.
"""
from core.models import Category, TransactionType

DEFAULTS = [
    ("Salary", TransactionType.INCOME),
    ("Freelance", TransactionType.INCOME),
    ("Other Income", TransactionType.INCOME),
    ("Food", TransactionType.EXPENSE),
    ("Transport", TransactionType.EXPENSE),
    ("Rent", TransactionType.EXPENSE),
    ("Utilities", TransactionType.EXPENSE),
    ("Entertainment", TransactionType.EXPENSE),
    ("Healthcare", TransactionType.EXPENSE),
    ("Shopping", TransactionType.EXPENSE),
]

for name, t in DEFAULTS:
    obj, created = Category.objects.get_or_create(name=name, type=t, user=None)
    print(("Created: " if created else "Exists:  ") + f"{name} ({t})")

print(f"\nTotal categories: {Category.objects.count()}")
