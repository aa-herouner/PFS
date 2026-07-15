from django.db import models

from core.models import BaseModel


class Transaction(BaseModel):
    """A single income or expense entry.

    Some transactions are auto-created from other modules (feed purchases,
    costed health records) and carry a non-MANUAL `source`; those are
    read-only in the finance UI (edited at their source record). Manual
    income/expense is entered directly in finance (Step 8).
    """

    class Type(models.TextChoices):
        INCOME = 'INCOME', 'Income'
        EXPENSE = 'EXPENSE', 'Expense'

    class Source(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual'
        FEED = 'FEED', 'Feed purchase'
        HEALTH = 'HEALTH', 'Health record'

    type = models.CharField(max_length=8, choices=Type.choices)
    # Category is a FK to either Income/ExpenseCategory; kept nullable so
    # auto-created rows (feed/health) don't strictly require one.
    expense_category = models.ForeignKey(
        'core.ExpenseCategory', on_delete=models.PROTECT,
        null=True, blank=True, related_name='transactions',
    )
    income_category = models.ForeignKey(
        'core.IncomeCategory', on_delete=models.PROTECT,
        null=True, blank=True, related_name='transactions',
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    batch = models.ForeignKey(
        'inventory.Batch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transactions',
    )
    party = models.CharField(max_length=150, blank=True, help_text='Customer or vendor.')
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.MANUAL)
    description = models.CharField(max_length=255, blank=True)
    # A bird-sale income transaction reduces its batch's current_quantity.
    is_bird_sale = models.BooleanField(default=False)

    # Links back to the originating record for auto-created transactions, so
    # updates/deletes at the source can find and sync their transaction.
    feed_purchase = models.OneToOneField(
        'feed.FeedPurchase', on_delete=models.CASCADE,
        null=True, blank=True, related_name='transaction',
    )
    health_record = models.OneToOneField(
        'health.HealthRecord', on_delete=models.CASCADE,
        null=True, blank=True, related_name='transaction',
    )

    class Meta:
        ordering = ('-date', '-id')

    def __str__(self):
        return f'{self.get_type_display()} {self.amount} on {self.date}'

    @property
    def is_readonly(self):
        """Auto-created transactions are edited at their source, not in finance."""
        return self.source != self.Source.MANUAL

    @property
    def category(self):
        return self.income_category if self.type == self.Type.INCOME else self.expense_category
