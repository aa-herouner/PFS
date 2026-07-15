from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel

EGGS_PER_CRATE = 30


class EggProduction(BaseModel):
    """Daily egg collection for a layer batch."""

    batch = models.ForeignKey('inventory.Batch', on_delete=models.CASCADE,
                              related_name='egg_production')
    date = models.DateField()
    eggs_collected = models.PositiveIntegerField()
    eggs_damaged = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-date', '-id')
        # One egg record per batch per day.
        constraints = [
            models.UniqueConstraint(fields=['batch', 'date'],
                                    name='unique_egg_record_per_batch_day'),
        ]

    def __str__(self):
        return f'{self.eggs_collected} eggs · {self.batch} · {self.date}'

    @property
    def crates(self):
        return Decimal(self.eggs_collected) / EGGS_PER_CRATE

    @property
    def hen_day_percentage(self):
        """eggs_collected / current birds × 100. Uses batch current_quantity."""
        birds = self.batch.current_quantity
        if not birds:
            return Decimal('0')
        return round(Decimal(self.eggs_collected) / birds * 100, 2)

    def clean(self):
        super().clean()
        errors = {}
        if self.date and self.date > date.today():
            errors['date'] = 'Date cannot be in the future.'
        if self.eggs_damaged is not None and self.eggs_collected is not None:
            if self.eggs_damaged > self.eggs_collected:
                errors['eggs_damaged'] = 'Damaged eggs cannot exceed eggs collected.'
        if errors:
            raise ValidationError(errors)


class WeightRecord(BaseModel):
    """Sample weighing for a broiler batch."""

    batch = models.ForeignKey('inventory.Batch', on_delete=models.CASCADE,
                              related_name='weight_records')
    date = models.DateField()
    sample_size = models.PositiveIntegerField(help_text='Number of birds weighed.')
    average_weight = models.DecimalField(
        max_digits=8, decimal_places=3,
        help_text='Average weight per bird (kg).')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-date', '-id')

    def __str__(self):
        return f'{self.average_weight}kg avg · {self.batch} · {self.date}'

    def clean(self):
        super().clean()
        errors = {}
        if self.date and self.date > date.today():
            errors['date'] = 'Date cannot be in the future.'
        if self.sample_size is not None and self.sample_size < 1:
            errors['sample_size'] = 'Sample size must be at least 1.'
        if self.average_weight is not None and self.average_weight <= 0:
            errors['average_weight'] = 'Average weight must be greater than zero.'
        if errors:
            raise ValidationError(errors)
