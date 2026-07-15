from datetime import date

from django import forms

from core.forms import StyledFormMixin

from .models import EggProduction, WeightRecord


class EggProductionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EggProduction
        fields = ('date', 'eggs_collected', 'eggs_damaged', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if batch is not None:
            self.instance.batch = batch
        if not self.instance.pk:
            self.fields['date'].initial = date.today()


class WeightRecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = WeightRecord
        fields = ('date', 'sample_size', 'average_weight', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if batch is not None:
            self.instance.batch = batch
        if not self.instance.pk:
            self.fields['date'].initial = date.today()
