from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def money(value):
    """Format a number as currency: symbol + thousands separators + 2 dp.

    e.g. 16500 -> '₦16,500.00', -75750 -> '-₦75,750.00', '' / None -> '—'.
    Currency symbol from settings.CURRENCY_SYMBOL (default '₦').
    """
    if value is None or value == '':
        return '—'
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    symbol = getattr(settings, 'CURRENCY_SYMBOL', '₦')
    sign = '-' if amount < 0 else ''
    return f'{sign}{symbol}{abs(amount):,.2f}'


@register.simple_tag
def col_value(obj, attr):
    """Resolve a column value by attribute or method name.

    Supports plain attributes (`name`) and no-arg methods such as
    `get_bird_type_display`. Returns '' for missing attributes.
    """
    value = getattr(obj, attr, '')
    if callable(value):
        value = value()
    return value
