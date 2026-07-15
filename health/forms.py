from datetime import date

from django import forms

from core.forms import StyledFormMixin
from core.models import BirdType

from .models import HealthRecord, VaccinationSchedule


class HealthRecordForm(StyledFormMixin, forms.ModelForm):
    """Health record entry. Batch supplied by the view.

    For a Vaccination, the vaccine name is chosen from the defined vaccination
    schedule (not free-typed). For Medication/Treatment there is no defined
    list, so `name` stays a text field. Both feed the model's single `name`.
    """

    # Not a model field: dropdown of scheduled vaccine names, shown only when
    # record type is Vaccination. Its value is copied into `name` in clean().
    vaccine_choice = forms.ChoiceField(
        required=False,
        label='Vaccine',
        help_text='Pick from the vaccination schedule. Manage the list under '
                  'Settings → Vaccination schedule.',
    )

    class Meta:
        model = HealthRecord
        fields = ('date', 'record_type', 'name', 'dosage', 'administered_by', 'cost', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'name': 'Drug / treatment name (used for Medication and Treatment).',
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = batch
        if batch is not None:
            self.instance.batch = batch
        if not self.instance.pk:
            self.fields['date'].initial = date.today()

        # Populate the vaccine dropdown from schedules applicable to this batch.
        schedules = VaccinationSchedule.objects.all()
        names = sorted({s.vaccine_name for s in schedules
                        if batch is None or s.applies_to(batch)})
        self.fields['vaccine_choice'].choices = (
            [('', '— Select a vaccine —')] + [(n, n) for n in names]
        )
        # The typed name field is only required for non-vaccination records;
        # let clean() decide, so neither field is unconditionally required.
        self.fields['name'].required = False
        # When editing an existing vaccination, preselect its vaccine.
        if self.instance.pk and self.instance.record_type == HealthRecord.RecordType.VACCINATION:
            self.fields['vaccine_choice'].initial = self.instance.name

    def clean(self):
        cleaned = super().clean()
        record_type = cleaned.get('record_type')
        if record_type == HealthRecord.RecordType.VACCINATION:
            vaccine = cleaned.get('vaccine_choice')
            if not vaccine:
                self.add_error('vaccine_choice', 'Select a vaccine from the schedule.')
            else:
                cleaned['name'] = vaccine
                self.instance.name = vaccine
        else:
            # Medication / Treatment: the typed name is required.
            if not cleaned.get('name'):
                self.add_error('name', 'Enter the drug / treatment name.')
        return cleaned


class VaccinationScheduleForm(StyledFormMixin, forms.ModelForm):
    # Multi-select checkboxes; stored on the model as a CSV string.
    bird_type = forms.MultipleChoiceField(
        choices=BirdType.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Bird types',
        help_text='Tick the bird types this vaccine applies to. '
                  'Leave all unticked to apply to any bird type.',
    )

    class Meta:
        model = VaccinationSchedule
        fields = ('vaccine_name', 'bird_type', 'breed', 'day_of_age', 'notes')
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-tick boxes from the stored CSV when editing.
        if self.instance and self.instance.pk:
            self.fields['bird_type'].initial = self.instance.bird_type_list

    def clean_bird_type(self):
        # MultipleChoiceField returns a list; store as a CSV string.
        return ','.join(self.cleaned_data['bird_type'])
