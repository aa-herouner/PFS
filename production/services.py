"""Production analytics: FCR and Chart.js trend data per batch."""
from decimal import Decimal

from django.db.models import Sum

from .models import EGGS_PER_CRATE, EggProduction, WeightRecord


def total_eggs(batch):
    return batch.egg_production.aggregate(t=Sum('eggs_collected'))['t'] or 0


def feed_conversion_ratio(batch):
    """FCR for a batch, computed per bird type. Returns a Decimal or None when
    there isn't enough data.

    - Layers: total feed (kg) ÷ total dozens of eggs (feed per dozen).
    - Broilers: total feed (kg) ÷ total weight gain (kg).
    """
    feed_kg = batch.total_feed_consumed  # Decimal
    if not feed_kg:
        return None

    if batch.bird_type == 'LAYER':
        eggs = total_eggs(batch)
        if not eggs:
            return None
        dozens = Decimal(eggs) / 12
        if dozens == 0:
            return None
        return round(feed_kg / dozens, 3)

    if batch.bird_type == 'BROILER':
        gain = total_weight_gain(batch)
        if not gain or gain <= 0:
            return None
        return round(feed_kg / gain, 3)

    return None


def total_weight_gain(batch):
    """Approximate total live-weight gain (kg) for a broiler batch:
    (latest avg weight − earliest avg weight) × current birds.

    Day-old chick weight isn't recorded, so gain is measured between the first
    and latest sample weighings. Returns Decimal or None.
    """
    records = list(batch.weight_records.order_by('date'))
    if len(records) < 1:
        return None
    earliest = records[0].average_weight
    latest = records[-1].average_weight
    per_bird_gain = Decimal(str(latest)) - Decimal(str(earliest))
    if per_bird_gain <= 0:
        return None
    return per_bird_gain * batch.current_quantity


def egg_trend(batch):
    """Chart.js series: dates + eggs collected (chronological)."""
    qs = batch.egg_production.order_by('date')
    return {
        'labels': [r.date.isoformat() for r in qs],
        'eggs': [r.eggs_collected for r in qs],
        'hen_day': [float(r.hen_day_percentage) for r in qs],
    }


def weight_trend(batch):
    """Chart.js series: dates + average weights (chronological)."""
    qs = batch.weight_records.order_by('date')
    return {
        'labels': [r.date.isoformat() for r in qs],
        'weights': [float(r.average_weight) for r in qs],
    }
