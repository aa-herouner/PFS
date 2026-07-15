from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from core.views import AuditFormMixin, BatchRecordDeleteView, BatchRecordUpdateView
from inventory.models import Batch

from .forms import EggProductionForm, WeightRecordForm
from .models import EggProduction, WeightRecord


class ProductionEntryView(LoginRequiredMixin, AuditFormMixin, CreateView):
    """Bird-type-aware production entry — attendant-accessible.

    Layers/breeders record egg production; broilers record sample weights.
    The batch (and therefore which form) comes from the URL.
    """

    template_name = 'production/production_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.batch = get_object_or_404(Batch, pk=kwargs['batch_pk'])
        self.is_layer = self.batch.bird_type in ('LAYER', 'BREEDER')
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return EggProductionForm if self.is_layer else WeightRecordForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['batch'] = self.batch
        return kwargs

    def get_success_url(self):
        return reverse('batch_detail', args=[self.batch.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Egg production recorded.' if self.is_layer else 'Weight recorded.',
        )
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batch'] = self.batch
        ctx['is_layer'] = self.is_layer
        ctx['title'] = 'Record egg production' if self.is_layer else 'Record sample weight'
        return ctx


class EggProductionUpdateView(BatchRecordUpdateView):
    model = EggProduction
    form_class = EggProductionForm
    template_name = 'production/production_form.html'
    verbose = 'egg production record'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_layer'] = True
        ctx['title'] = 'Edit egg production'
        return ctx


class EggProductionDeleteView(BatchRecordDeleteView):
    model = EggProduction
    verbose = 'egg production record'


class WeightRecordUpdateView(BatchRecordUpdateView):
    model = WeightRecord
    form_class = WeightRecordForm
    template_name = 'production/production_form.html'
    verbose = 'weight record'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_layer'] = False
        ctx['title'] = 'Edit sample weight'
        return ctx


class WeightRecordDeleteView(BatchRecordDeleteView):
    model = WeightRecord
    verbose = 'weight record'
