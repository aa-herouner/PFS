"""Financial aggregates: profit/loss, cost per bird, income vs expense."""
from decimal import Decimal

from django.db.models import Sum

from .models import Transaction


def _sum(qs, txn_type):
    agg = qs.filter(type=txn_type).aggregate(t=Sum('amount'))
    return agg['t'] or Decimal('0')


def totals(qs=None):
    """Income, expense and profit for a transaction queryset (default: all)."""
    qs = Transaction.objects.all() if qs is None else qs
    income = _sum(qs, Transaction.Type.INCOME)
    expense = _sum(qs, Transaction.Type.EXPENSE)
    return {'income': income, 'expense': expense, 'profit': income - expense}


def batch_profit_loss(batch):
    """P&L for a single batch. Expense includes the batch's own transactions
    (feed/health/manual) plus its acquisition cost."""
    qs = batch.transactions.all()
    t = totals(qs)
    acquisition = batch.total_cost
    t['acquisition_cost'] = acquisition
    t['expense_with_acquisition'] = t['expense'] + acquisition
    t['net'] = t['income'] - t['expense_with_acquisition']
    birds = batch.initial_quantity or 1
    t['cost_per_bird'] = round(t['expense_with_acquisition'] / birds, 2)
    return t


def period_summary(start=None, end=None):
    """Farm-wide totals optionally filtered to a [start, end] date range."""
    qs = Transaction.objects.all()
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    return totals(qs)


def expense_by_category(start=None, end=None):
    """Expense totals grouped by expense category name (for charts/reports)."""
    qs = Transaction.objects.filter(type=Transaction.Type.EXPENSE)
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    rows = (
        qs.values('expense_category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    return [
        {'category': r['expense_category__name'] or 'Uncategorised', 'total': r['total']}
        for r in rows
    ]
