"""Dashboard aggregates — assembled from the per-app service functions."""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from core.models import FeedType
from feed.models import LOW_STOCK_THRESHOLD_KG, feed_stock_level
from finance.services import expense_by_category, period_summary
from health.services import due_vaccinations
from inventory.models import Batch, MortalityRecord
from production.models import EggProduction, WeightRecord

# A day's mortality above this % of a batch's current birds is "abnormal".
MORTALITY_SPIKE_PCT = Decimal('2')


def active_batches():
    return Batch.objects.filter(status=Batch.Status.ACTIVE)


def kpis():
    batches = list(active_batches().select_related('breed'))
    total_birds = sum(b.current_quantity for b in batches)
    total_initial = sum(b.initial_quantity for b in batches)
    total_lost = sum(b.total_mortality + b.total_culls for b in batches)
    mortality_rate = (
        round(Decimal(total_lost) / total_initial * 100, 2) if total_initial else Decimal('0')
    )

    today = date.today()
    week_ago = today - timedelta(days=7)
    eggs_today = EggProduction.objects.filter(date=today).aggregate(
        t=Sum('eggs_collected'))['t'] or 0
    eggs_week = EggProduction.objects.filter(date__gte=week_ago).aggregate(
        t=Sum('eggs_collected'))['t'] or 0

    # Latest broiler average weight (across active broiler batches).
    broiler_ids = [b.pk for b in batches if b.bird_type == 'BROILER']
    latest_weight = (
        WeightRecord.objects.filter(batch_id__in=broiler_ids).order_by('-date').first()
        if broiler_ids else None
    )

    month_start = today.replace(day=1)
    mtd = period_summary(start=month_start, end=today)

    return {
        'total_birds': total_birds,
        'active_batches': len(batches),
        'mortality_rate': mortality_rate,
        'eggs_today': eggs_today,
        'eggs_week': eggs_week,
        'broiler_avg_weight': latest_weight.average_weight if latest_weight else None,
        'mtd': mtd,
    }


def feed_stock_status():
    rows = []
    for ft in FeedType.objects.all():
        level = feed_stock_level(ft)
        rows.append({'feed_type': ft, 'level': level, 'low': level <= LOW_STOCK_THRESHOLD_KG})
    return rows


def mortality_trend(days=30):
    """Farm-wide daily mortality (incl. culls) for the last `days` days."""
    start = date.today() - timedelta(days=days)
    qs = (
        MortalityRecord.objects.filter(date__gte=start)
        .values('date')
        .annotate(total=Sum('quantity'))
        .order_by('date')
    )
    return {
        'labels': [r['date'].isoformat() for r in qs],
        'counts': [r['total'] for r in qs],
    }


def egg_production_trend(days=30):
    start = date.today() - timedelta(days=days)
    qs = (
        EggProduction.objects.filter(date__gte=start)
        .values('date')
        .annotate(total=Sum('eggs_collected'))
        .order_by('date')
    )
    return {
        'labels': [r['date'].isoformat() for r in qs],
        'eggs': [r['total'] for r in qs],
    }


def alerts():
    """Farm-wide alerts: low feed stock, vaccinations due/overdue, mortality spikes."""
    items = []

    for row in feed_stock_status():
        if row['low']:
            items.append({
                'level': 'warning',
                'message': f"Low feed stock: {row['feed_type'].name} "
                           f"({row['level']} {row['feed_type'].unit} left)",
            })

    for a in due_vaccinations():
        verb = 'overdue' if a['status'] == 'overdue' else 'due soon'
        items.append({
            'level': 'danger' if a['status'] == 'overdue' else 'warning',
            'message': f"Vaccination {verb}: {a['schedule'].vaccine_name} "
                       f"for {a['batch'].batch_code}",
        })

    # Mortality spike: today's mortality above threshold % of current birds.
    today = date.today()
    for batch in active_batches():
        todays = batch.mortality_records.filter(date=today).aggregate(
            t=Sum('quantity'))['t'] or 0
        birds = batch.current_quantity + todays  # birds present before today's loss
        if birds and Decimal(todays) / birds * 100 >= MORTALITY_SPIKE_PCT:
            items.append({
                'level': 'danger',
                'message': f"Mortality spike in {batch.batch_code}: "
                           f"{todays} bird(s) today",
            })

    return items


def expense_breakdown():
    return expense_by_category()
