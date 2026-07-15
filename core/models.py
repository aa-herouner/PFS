from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """Abstract base giving every domain model an audit trail.

    `created_by` / `updated_by` are set from `request.user` in views/forms;
    they are nullable so system/seed-created rows and migrations don't break.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Reference data (owner-managed lookups selectable in later forms)
# ---------------------------------------------------------------------------

class BirdType(models.TextChoices):
    LAYER = 'LAYER', 'Layer'
    BROILER = 'BROILER', 'Broiler'
    BREEDER = 'BREEDER', 'Breeder'


class Breed(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    bird_type = models.CharField(max_length=10, choices=BirdType.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} ({self.get_bird_type_display()})'


class Pen(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField(help_text='Maximum birds this pen holds.')
    description = models.TextField(blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class FeedType(BaseModel):
    class Category(models.TextChoices):
        STARTER = 'STARTER', 'Starter'
        GROWER = 'GROWER', 'Grower'
        FINISHER = 'FINISHER', 'Finisher'
        LAYER_MASH = 'LAYER_MASH', 'Layer mash'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=12, choices=Category.choices)
    unit = models.CharField(max_length=20, default='kg')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class ExpenseCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'expense categories'

    def __str__(self):
        return self.name


class IncomeCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'income categories'

    def __str__(self):
        return self.name
