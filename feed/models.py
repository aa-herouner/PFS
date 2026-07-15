from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from core.models import BaseModel

LOW_STOCK_THRESHOLD_KG = Decimal('50')


class FeedPurchase(BaseModel):
    """A purchase of feed. Auto-creates a matching EXPENSE transaction on save
    (see feed.signals)."""

    feed_type = models.ForeignKey('core.FeedType', on_delete=models.PROTECT,
                                  related_name='purchases')
    date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2,
                                   help_text='Quantity purchased (in feed-type unit, usually kg).')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ('-date', '-id')

    def __str__(self):
        return f'{self.quantity} {self.feed_type} on {self.date}'

    @property
    def total_cost(self):
        return Decimal(str(self.quantity)) * Decimal(str(self.unit_cost))

    def clean(self):
        super().clean()
        errors = {}
        if self.date and self.date > date.today():
            errors['date'] = 'Date cannot be in the future.'
        if self.quantity is not None and self.quantity <= 0:
            errors['quantity'] = 'Quantity must be greater than zero.'
        if self.unit_cost is not None and self.unit_cost < 0:
            errors['unit_cost'] = 'Unit cost cannot be negative.'
        if errors:
            raise ValidationError(errors)


class FeedConsumption(BaseModel):
    """Feed consumed by a batch on a date."""

    batch = models.ForeignKey('inventory.Batch', on_delete=models.CASCADE,
                              related_name='feed_consumption')
    feed_type = models.ForeignKey('core.FeedType', on_delete=models.PROTECT,
                                  related_name='consumption')
    date = models.DateField()
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ('-date', '-id')

    def __str__(self):
        return f'{self.quantity_kg} {self.feed_type} → {self.batch} on {self.date}'

    def clean(self):
        super().clean()
        errors = {}
        if self.date and self.date > date.today():
            errors['date'] = 'Date cannot be in the future.'
        if self.quantity_kg is not None and self.quantity_kg <= 0:
            errors['quantity_kg'] = 'Quantity must be greater than zero.'
        # Consumption must not exceed the feed type's available stock.
        if self.feed_type_id and self.quantity_kg:
            available = feed_stock_level(self.feed_type)
            if self.pk:
                previous = FeedConsumption.objects.get(pk=self.pk).quantity_kg
                available += previous
            if self.quantity_kg > available:
                errors['quantity_kg'] = (
                    f'Only {available} in stock for {self.feed_type}; '
                    f'cannot consume {self.quantity_kg}.'
                )
        if errors:
            raise ValidationError(errors)


def feed_stock_level(feed_type):
    """Current stock for a feed type = total purchased − total consumed."""
    purchased = FeedPurchase.objects.filter(feed_type=feed_type).aggregate(
        t=Sum('quantity'))['t'] or Decimal('0')
    consumed = FeedConsumption.objects.filter(feed_type=feed_type).aggregate(
        t=Sum('quantity_kg'))['t'] or Decimal('0')
    return purchased - consumed
