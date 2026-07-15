"""Report builders. Each returns a uniform dict:
    {'title', 'headers': [...], 'rows': [[...], ...], 'meta': {...}}
so a single Excel/PDF exporter handles every report.
"""
from finance.services import batch_profit_loss, period_summary
from inventory.models import Batch, MortalityRecord
from feed.models import FeedConsumption, FeedPurchase
from production.models import EggProduction, WeightRecord
from production.services import feed_conversion_ratio


def _date_filter(qs, field, start, end):
    if start:
        qs = qs.filter(**{f'{field}__gte': start})
    if end:
        qs = qs.filter(**{f'{field}__lte': end})
    return qs


def batch_performance_report(start=None, end=None):
    rows = []
    for b in Batch.objects.select_related('breed'):
        rows.append([
            b.batch_code, b.breed.name, b.get_bird_type_display(),
            b.get_status_display(), b.initial_quantity, b.current_quantity,
            b.age_in_weeks, f'{b.mortality_rate}%',
            feed_conversion_ratio(b) or '—',
        ])
    return {
        'title': 'Batch performance',
        'headers': ['Code', 'Breed', 'Type', 'Status', 'Initial', 'Current',
                    'Age (wk)', 'Mortality', 'FCR'],
        'rows': rows,
        'meta': {'start': start, 'end': end},
    }


def mortality_report(start=None, end=None):
    qs = _date_filter(
        MortalityRecord.objects.select_related('batch'), 'date', start, end)
    rows = [[
        r.date, r.batch.batch_code, r.get_record_type_display(),
        r.quantity, r.cause or '—',
    ] for r in qs]
    return {
        'title': 'Mortality & culls',
        'headers': ['Date', 'Batch', 'Type', 'Quantity', 'Cause'],
        'rows': rows,
        'meta': {'start': start, 'end': end, 'total': sum(r[3] for r in rows)},
    }


def feed_report(start=None, end=None):
    purchases = _date_filter(
        FeedPurchase.objects.select_related('feed_type'), 'date', start, end)
    consumption = _date_filter(
        FeedConsumption.objects.select_related('feed_type', 'batch'), 'date', start, end)
    rows = []
    for p in purchases:
        rows.append([p.date, 'Purchase', p.feed_type.name, '—', p.quantity, p.total_cost])
    for c in consumption:
        rows.append([c.date, 'Consumption', c.feed_type.name, c.batch.batch_code,
                     c.quantity_kg, '—'])
    rows.sort(key=lambda r: str(r[0]))
    return {
        'title': 'Feed usage',
        'headers': ['Date', 'Kind', 'Feed type', 'Batch', 'Quantity', 'Cost'],
        'rows': rows,
        'meta': {'start': start, 'end': end},
    }


def production_report(start=None, end=None):
    eggs = _date_filter(
        EggProduction.objects.select_related('batch'), 'date', start, end)
    weights = _date_filter(
        WeightRecord.objects.select_related('batch'), 'date', start, end)
    rows = []
    for e in eggs:
        rows.append([e.date, e.batch.batch_code, 'Eggs', e.eggs_collected,
                     f'{e.hen_day_percentage}%'])
    for w in weights:
        rows.append([w.date, w.batch.batch_code, 'Weight', w.average_weight, '—'])
    rows.sort(key=lambda r: str(r[0]))
    return {
        'title': 'Production',
        'headers': ['Date', 'Batch', 'Kind', 'Value', 'Hen-day %'],
        'rows': rows,
        'meta': {'start': start, 'end': end},
    }


def financial_report(start=None, end=None):
    summary = period_summary(start, end)
    rows = []
    for b in Batch.objects.select_related('breed'):
        pl = batch_profit_loss(b)
        rows.append([
            b.batch_code, pl['income'], pl['expense_with_acquisition'],
            pl['net'], pl['cost_per_bird'],
        ])
    return {
        'title': 'Financial (P&L)',
        'headers': ['Batch', 'Income', 'Expense', 'Net', 'Cost/bird'],
        'rows': rows,
        'meta': {
            'start': start, 'end': end,
            'income': summary['income'], 'expense': summary['expense'],
            'profit': summary['profit'],
        },
    }


# Registry so views/exports can look a report up by slug.
REPORTS = {
    'batch-performance': batch_performance_report,
    'mortality': mortality_report,
    'feed': feed_report,
    'production': production_report,
    'financial': financial_report,
}
