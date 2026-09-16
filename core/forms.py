from django import forms

from .models import Category, Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["title", "amount", "transaction_type", "category", "date", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Grocery shopping"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "transaction_type": forms.Select(attrs={"class": "form-select", "id": "id_transaction_type"}),
            "category": forms.Select(attrs={"class": "form-select", "id": "id_category"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None:
            # Show global categories (user=None) plus the user's own.
            self.fields["category"].queryset = (
                Category.objects.filter(user__isnull=True) | Category.objects.filter(user=user)
            ).distinct()

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        transaction_type = cleaned_data.get("transaction_type")
        if category and transaction_type and category.type != transaction_type:
            self.add_error(
                "category",
                f"'{category.name}' is a {category.get_type_display()} category and doesn't match "
                f"the selected transaction type.",
            )
        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "type"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Groceries"}),
            "type": forms.Select(attrs={"class": "form-select"}),
        }


class DateRangeFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    category = forms.ModelChoiceField(
        required=False, queryset=Category.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    transaction_type = forms.ChoiceField(
        required=False,
        choices=[("", "All Types")] + list(Transaction._meta.get_field("transaction_type").choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = (
                Category.objects.filter(user__isnull=True) | Category.objects.filter(user=user)
            ).distinct()
