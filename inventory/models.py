from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Sum

from core.models import BaseModel, BirdType


class Batch(BaseModel):
    """A flock / batch of birds acquired together."""

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SOLD = 'SOLD', 'Sold'
        DEPOPULATED = 'DEPOPULATED', 'Depopulated'

    batch_code = models.CharField(
        max_length=50, unique=True, blank=True,
        help_text='Auto-generated (e.g. BRO-2026-001) if left blank.')
    breed = models.ForeignKey('core.Breed', on_delete=models.PROTECT, related_name='batches')
    bird_type = models.CharField(max_length=10, choices=BirdType.choices)
    supplier = models.CharField(max_length=150, blank=True)
    date_acquired = models.DateField()
    initial_quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2,
                                    help_text='Cost per bird at acquisition.')
    pen = models.ForeignKey('core.Pen', on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='batches')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-date_acquired', 'batch_code')
        verbose_name_plural = 'batches'

    def __str__(self):
        return self.batch_code

    # --- batch code generation --------------------------------------------
    @staticmethod
    def _code_prefix(bird_type):
        """3-letter prefix from the bird type (BROILER→BRO, LAYER→LAY, BREEDER→BRE)."""
        return (bird_type or 'GEN')[:3].upper()

    @classmethod
    def generate_batch_code(cls, bird_type, year=None):
        """Next unique code for this bird type + year, e.g. 'BRO-2026-001'.

        Sequence is per (prefix, year): finds the highest existing sequence for
        that prefix/year and adds one. Callers must still be prepared for the
        unique constraint under concurrency — `save()` retries on collision.
        """
        prefix = cls._code_prefix(bird_type)
        year = year or date.today().year
        stem = f'{prefix}-{year}-'
        last = (cls.objects.filter(batch_code__startswith=stem)
                .order_by('-batch_code').values_list('batch_code', flat=True).first())
        seq = 1
        if last:
            try:
                seq = int(last.rsplit('-', 1)[1]) + 1
            except (ValueError, IndexError):
                seq = cls.objects.filter(batch_code__startswith=stem).count() + 1
        return f'{stem}{seq:03d}'

    def save(self, *args, **kwargs):
        if not self.batch_code:
            year = self.date_acquired.year if self.date_acquired else None
            # Retry on the off chance a concurrent insert grabbed the same code.
            for _ in range(5):
                self.batch_code = self.generate_batch_code(self.bird_type, year)
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.batch_code = ''
                    continue
            # Final attempt: let any IntegrityError surface rather than loop forever.
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        if self.date_acquired and self.date_acquired > date.today():
            errors['date_acquired'] = 'Acquisition date cannot be in the future.'
        if self.initial_quantity is not None and self.initial_quantity < 1:
            errors['initial_quantity'] = 'Initial quantity must be at least 1.'
        # A batch cannot hold more birds than the pen it sits in can take.
        # Other active batches already placed in the same pen count against it.
        if self.pen_id and self.initial_quantity:
            capacity = self.pen.capacity
            others = (Batch.objects
                      .filter(pen_id=self.pen_id, status=Batch.Status.ACTIVE)
                      .exclude(pk=self.pk)
                      .aggregate(t=Sum('initial_quantity'))['t'] or 0)
            available = capacity - others
            if self.initial_quantity > available:
                if others:
                    errors['initial_quantity'] = (
                        f'{self.pen} holds {capacity} bird(s) and already has '
                        f'{others} placed; only {max(available, 0)} space(s) left, '
                        f'cannot add {self.initial_quantity}.'
                    )
                else:
                    errors['initial_quantity'] = (
                        f'{self.pen} holds at most {capacity} bird(s); '
                        f'cannot place {self.initial_quantity}.'
                    )
        if errors:
            raise ValidationError(errors)

    # --- derived quantities ------------------------------------------------
    def _sum(self, record_type):
        agg = self.mortality_records.filter(record_type=record_type).aggregate(t=Sum('quantity'))
        return agg['t'] or 0

    @property
    def total_mortality(self):
        return self._sum(MortalityRecord.RecordType.MORTALITY)

    @property
    def total_culls(self):
        return self._sum(MortalityRecord.RecordType.CULL)

    @property
    def total_sold(self):
        """Birds sold against this batch via bird-sale income transactions."""
        agg = self.transactions.filter(is_bird_sale=True).aggregate(t=Sum('quantity'))
        total = agg['t'] or 0
        # quantity is a Decimal on Transaction; bird counts are whole numbers.
        return int(total)

    @property
    def current_quantity(self):
        qty = self.initial_quantity - self.total_mortality - self.total_culls - self.total_sold
        return max(qty, 0)

    @property
    def total_removed(self):
        return self.total_mortality + self.total_culls + self.total_sold

    @property
    def age_in_days(self):
        return (date.today() - self.date_acquired).days

    @property
    def age_in_weeks(self):
        return self.age_in_days // 7

    @property
    def mortality_rate(self):
        """Mortality (incl. culls) as a percent of initial quantity."""
        if not self.initial_quantity:
            return 0
        return round((self.total_mortality + self.total_culls) / self.initial_quantity * 100, 2)

    @property
    def total_cost(self):
        # Coerce unit_cost to Decimal: on a freshly-created (unsaved-value)
        # instance it may still be the raw string passed to create().
        return self.initial_quantity * Decimal(str(self.unit_cost))

    @property
    def total_feed_consumed(self):
        """Total kg of feed consumed by this batch (across feed types)."""
        agg = self.feed_consumption.aggregate(t=Sum('quantity_kg'))
        return agg['t'] or Decimal('0')

    @property
    def total_health_cost(self):
        """Total cost of health records against this batch."""
        agg = self.health_records.aggregate(t=Sum('cost'))
        return agg['t'] or Decimal('0')


class MortalityRecord(BaseModel):
    """A daily mortality or cull event against a batch."""

    class RecordType(models.TextChoices):
        MORTALITY = 'MORTALITY', 'Mortality'
        CULL = 'CULL', 'Cull'

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='mortality_records')
    date = models.DateField()
    quantity = models.PositiveIntegerField()
    record_type = models.CharField(max_length=10, choices=RecordType.choices,
                                   default=RecordType.MORTALITY)
    cause = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-date', '-id')

    def __str__(self):
        return f'{self.get_record_type_display()} ×{self.quantity} on {self.date} ({self.batch})'

    def clean(self):
        super().clean()
        errors = {}
        if self.date and self.date > date.today():
            errors['date'] = 'Date cannot be in the future.'
        if self.quantity is not None and self.quantity < 1:
            errors['quantity'] = 'Quantity must be at least 1.'
        # quantity must not exceed birds currently available in the batch.
        if self.batch_id and self.quantity:
            available = self.batch.current_quantity
            # On edit, add back this record's previous quantity so it isn't
            # double-counted against itself.
            if self.pk:
                previous = MortalityRecord.objects.get(pk=self.pk).quantity
                available += previous
            if self.quantity > available:
                errors['quantity'] = (
                    f'Only {available} bird(s) available in this batch; '
                    f'cannot record {self.quantity}.'
                )
        if errors:
            raise ValidationError(errors)
