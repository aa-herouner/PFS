import json
from datetime import date

from django import forms

from core.forms import StyledFormMixin
from core.models import FeedType

from .models import FeedConsumption, FeedPurchase


class FeedPurchaseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FeedPurchase
        fields = ('feed_type', 'date', 'quantity', 'unit_cost', 'supplier')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}
        help_texts = {
            'unit_cost': 'Prefilled from the feed type’s price in settings. '
                         'Change it if this purchase cost a different amount.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['date'].initial = date.today()

    @property
    def feed_type_prices(self):
        """JSON map {feed_type_id: default unit_cost} for prefill in the template."""
        return json.dumps({ft.pk: str(ft.unit_cost) for ft in FeedType.objects.all()})


class FeedConsumptionForm(StyledFormMixin, forms.ModelForm):
    """Daily consumption entry. Batch supplied by the view."""

    class Meta:
        model = FeedConsumption
        fields = ('feed_type', 'date', 'quantity_kg')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if batch is not None:
            self.instance.batch = batch
        if not self.instance.pk:
            self.fields['date'].initial = date.today()
