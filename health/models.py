from datetime import date

from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel, BirdType


class HealthRecord(BaseModel):
    """A vaccination / medication / treatment event against a batch.

    A record with a cost auto-creates an EXPENSE transaction (see
    health.signals), same 'no double entry' pattern as feed purchases.
    """

    class RecordType(models.TextChoices):
        VACCINATION = 'VACCINATION', 'Vaccination'
        MEDICATION = 'MEDICATION', 'Medication'
        TREATMENT = 'TREATMENT', 'Treatment'

    batch = models.ForeignKey('inventory.Batch', on_delete=models.CASCADE,
                              related_name='health_records')
    date = models.DateField()
    record_type = models.CharField(max_length=12, choices=RecordType.choices)
    name = models.CharField(max_length=150, help_text='Vaccine / drug / treatment name.')
    dosage = models.CharField(max_length=100, blank=True)
    administered_by = models.CharField(max_length=150, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-date', '-id')

    def __str__(self):
        return f'{self.get_record_type_display()}: {self.name} ({self.batch})'

    def clean(self):
        super().clean()
        errors = {}
        if self.date and self.date > date.today():
            errors['date'] = 'Date cannot be in the future.'
        if self.cost is not None and self.cost < 0:
            errors['cost'] = 'Cost cannot be negative.'
        if errors:
            raise ValidationError(errors)


class VaccinationSchedule(BaseModel):
    """Defines when a vaccine is due, by bird type and/or breed and day of age.

    Used to compute upcoming/overdue vaccinations per active batch by comparing
    the batch's age in days to `day_of_age`.
    """

    # Comma-separated BirdType codes (e.g. "LAYER,BROILER"). Blank = all types.
    bird_type = models.CharField(max_length=40, blank=True,
                                 help_text='Tick the bird types this vaccine applies to. '
                                           'Leave all unticked to apply to any bird type.')
    breed = models.ForeignKey('core.Breed', on_delete=models.CASCADE,
                              null=True, blank=True, related_name='vaccination_schedules',
                              help_text='Optional: restrict to a specific breed.')
    vaccine_name = models.CharField(max_length=150)
    day_of_age = models.PositiveIntegerField(help_text='Age in days when this vaccine is due.')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('day_of_age', 'vaccine_name')

    def __str__(self):
        return f'{self.vaccine_name} @ day {self.day_of_age}'

    @property
    def bird_type_list(self):
        """The selected bird-type codes as a list ([] means 'any type')."""
        return [t for t in self.bird_type.split(',') if t]

    @property
    def bird_type_display(self):
        """Human-readable bird types for lists/tables ('Any' if unrestricted)."""
        labels = dict(BirdType.choices)
        selected = self.bird_type_list
        return ', '.join(labels.get(t, t) for t in selected) if selected else 'Any'

    def applies_to(self, batch):
        """Whether this schedule entry applies to the given batch."""
        types = self.bird_type_list
        if types and batch.bird_type not in types:
            return False
        if self.breed_id and self.breed_id != batch.breed_id:
            return False
        return True
