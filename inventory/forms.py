import json
from datetime import date

from django import forms

from core.forms import StyledFormMixin
from core.models import BirdType

from .models import Batch, MortalityRecord


class BatchForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Batch
        fields = (
            'batch_code', 'breed', 'bird_type', 'supplier', 'date_acquired',
            'initial_quantity', 'unit_cost', 'pen', 'status', 'notes',
        )
        widgets = {
            'date_acquired': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'batch_code': 'Auto-generated from bird type and year. '
                          'Leave as suggested, or edit it if you must.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Code is optional on input: blank ⇒ the model generates one on save.
        self.fields['batch_code'].required = False

    @property
    def suggested_codes(self):
        """JSON map {bird_type: next code} so the form can prefill on new batches."""
        return json.dumps({bt: Batch.generate_batch_code(bt) for bt, _ in BirdType.choices})

    def clean_date_acquired(self):
        d = self.cleaned_data['date_acquired']
        if d and d > date.today():
            raise forms.ValidationError('Acquisition date cannot be in the future.')
        return d

    def clean_initial_quantity(self):
        q = self.cleaned_data['initial_quantity']
        if q is not None and q < 1:
            raise forms.ValidationError('Initial quantity must be at least 1.')
        return q


class MortalityForm(StyledFormMixin, forms.ModelForm):
    """Daily mortality / cull entry. The batch is supplied by the view, not
    the form, so it is set on the instance before model validation runs."""

    class Meta:
        model = MortalityRecord
        fields = ('date', 'record_type', 'quantity', 'cause', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if batch is not None:
            self.instance.batch = batch
        self.fields['date'].initial = date.today()
