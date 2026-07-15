from datetime import date
from decimal import Decimal

from django import forms

from core.forms import StyledFormMixin

from .models import Transaction


class TransactionForm(StyledFormMixin, forms.ModelForm):
    """Manual income/expense entry.

    - INCOME requires an income category; EXPENSE an expense category.
    - Tick 'is_bird_sale' (INCOME with a batch + quantity) to reduce that
      batch's bird count; quantity is validated against current birds.
    """

    class Meta:
        model = Transaction
        fields = (
            'type', 'date', 'amount', 'income_category', 'expense_category',
            'batch', 'is_bird_sale', 'quantity', 'unit_price', 'party', 'description',
        )
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['date'].initial = date.today()

    def clean(self):
        cleaned = super().clean()
        txn_type = cleaned.get('type')
        income_cat = cleaned.get('income_category')
        expense_cat = cleaned.get('expense_category')
        batch = cleaned.get('batch')
        is_bird_sale = cleaned.get('is_bird_sale')
        quantity = cleaned.get('quantity')
        date_ = cleaned.get('date')

        if date_ and date_ > date.today():
            self.add_error('date', 'Date cannot be in the future.')

        if txn_type == Transaction.Type.INCOME:
            if not income_cat:
                self.add_error('income_category', 'Select an income category.')
            cleaned['expense_category'] = None
        elif txn_type == Transaction.Type.EXPENSE:
            if not expense_cat:
                self.add_error('expense_category', 'Select an expense category.')
            cleaned['income_category'] = None

        if is_bird_sale:
            if txn_type != Transaction.Type.INCOME:
                self.add_error('is_bird_sale', 'Bird sales must be income.')
            if not batch:
                self.add_error('batch', 'Select the batch the birds were sold from.')
            if not quantity or quantity <= 0:
                self.add_error('quantity', 'Enter the number of birds sold.')
            elif batch:
                # On edit, add back this sale's own previous quantity.
                available = batch.current_quantity
                if self.instance.pk:
                    prev = Transaction.objects.get(pk=self.instance.pk)
                    if prev.is_bird_sale and prev.batch_id == batch.pk:
                        available += int(prev.quantity or 0)
                if quantity > available:
                    self.add_error(
                        'quantity',
                        f'Only {available} bird(s) available in {batch.batch_code}.',
                    )
        return cleaned
