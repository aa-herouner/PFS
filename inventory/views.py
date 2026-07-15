from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.access import ManagementRequiredMixin
from core.models import BirdType
from core.views import AuditFormMixin, BatchRecordDeleteView, BatchRecordUpdateView

from .forms import BatchForm, MortalityForm
from .models import Batch, MortalityRecord


class BatchListView(LoginRequiredMixin, ListView):
    """All roles can view the flock list."""

    model = Batch
    template_name = 'inventory/batch_list.html'
    context_object_name = 'batches'

    def get_queryset(self):
        qs = super().get_queryset().select_related('breed', 'pen')
        params = self.request.GET
        search = params.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(batch_code__icontains=search)
                | Q(supplier__icontains=search)
                | Q(breed__name__icontains=search)
            )
        bird_type = params.get('bird_type', '').strip()
        if bird_type:
            qs = qs.filter(bird_type=bird_type)
        status = params.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['headers'] = ['Code', 'Breed', 'Type', 'Current', 'Age', 'Status']
        ctx['bird_types'] = BirdType.choices
        ctx['statuses'] = Batch.Status.choices
        ctx['filters'] = {
            'q': self.request.GET.get('q', ''),
            'bird_type': self.request.GET.get('bird_type', ''),
            'status': self.request.GET.get('status', ''),
        }
        return ctx


class BatchDetailView(LoginRequiredMixin, DetailView):
    """Aggregates mortality (and, in later steps, feed/health/production/
    finance) for one flock. All roles can view."""

    model = Batch
    template_name = 'inventory/batch_detail.html'
    context_object_name = 'batch'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        batch = self.object
        user = self.request.user
        can_manage = user.is_superuser or user.role in ('OWNER', 'MANAGER')
        ctx['can_manage'] = can_manage
        # Management gets an extra actions (edit/delete) column on record tables.
        actions = [''] if can_manage else []
        ctx['current_birds_hint'] = f'of {batch.initial_quantity} at start'
        ctx['mortality_records'] = batch.mortality_records.all()[:20]
        ctx['mortality_headers'] = ['Date', 'Type', 'Quantity', 'Cause'] + actions
        ctx['health_records'] = batch.health_records.all()[:20]
        ctx['health_headers'] = ['Date', 'Type', 'Name', 'Cost'] + actions
        # Vaccination status for this batch (import here to avoid a hard
        # inventory→health dependency at module load).
        from health.services import batch_vaccination_status
        ctx['vaccination_status'] = batch_vaccination_status(batch)

        # Production (import locally for the same reason).
        from production.services import (
            egg_trend,
            feed_conversion_ratio,
            weight_trend,
        )
        ctx['is_layer'] = batch.bird_type in ('LAYER', 'BREEDER')
        ctx['fcr'] = feed_conversion_ratio(batch)
        if ctx['is_layer']:
            ctx['egg_records'] = batch.egg_production.all()[:20]
            ctx['egg_headers'] = ['Date', 'Collected', 'Damaged', 'Hen-day %'] + actions
            ctx['trend'] = egg_trend(batch)
        else:
            ctx['weight_records'] = batch.weight_records.all()[:20]
            ctx['weight_headers'] = ['Date', 'Sample', 'Avg weight (kg)'] + actions
            ctx['trend'] = weight_trend(batch)

        # Per-batch P&L for management roles.
        if can_manage:
            from finance.services import batch_profit_loss
            ctx['pl'] = batch_profit_loss(batch)
        return ctx


class BatchCreateView(ManagementRequiredMixin, AuditFormMixin, CreateView):
    model = Batch
    form_class = BatchForm
    template_name = 'inventory/batch_form.html'

    def get_success_url(self):
        return reverse('batch_detail', args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Batch "{self.object.batch_code}" registered.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Register batch'
        return ctx


class BatchUpdateView(ManagementRequiredMixin, AuditFormMixin, UpdateView):
    model = Batch
    form_class = BatchForm
    template_name = 'inventory/batch_form.html'

    def get_success_url(self):
        return reverse('batch_detail', args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Batch "{self.object.batch_code}" updated.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit batch'
        return ctx


class BatchStatusUpdateView(ManagementRequiredMixin, View):
    """Disable/close (or reopen) a flock by changing its status.

    POST-only with a `status` field. Instead of deleting a flock — which would
    cascade its records and finance entries — this marks it Sold or Depopulated
    (or back to Active), keeping all history intact.
    """

    def post(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk)
        target = request.POST.get('status')
        valid = {Batch.Status.ACTIVE, Batch.Status.SOLD, Batch.Status.DEPOPULATED}
        if target not in valid:
            messages.error(request, 'Invalid status.')
        else:
            batch.status = target
            batch.updated_by = request.user
            batch.save(update_fields=['status', 'updated_by', 'updated_at'])
            messages.success(
                request,
                f'Flock "{batch.batch_code}" marked {batch.get_status_display()}.',
            )
        return redirect('batch_detail', pk=batch.pk)


class MortalityUpdateView(BatchRecordUpdateView):
    model = MortalityRecord
    form_class = MortalityForm
    template_name = 'inventory/mortality_form.html'
    verbose = 'mortality record'


class MortalityDeleteView(BatchRecordDeleteView):
    model = MortalityRecord
    verbose = 'mortality record'


class MortalityCreateView(LoginRequiredMixin, AuditFormMixin, CreateView):
    """Daily mortality / cull entry — attendant-accessible."""

    model = MortalityRecord
    form_class = MortalityForm
    template_name = 'inventory/mortality_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.batch = get_object_or_404(Batch, pk=kwargs['batch_pk'])
        return super().dispatch(request, *args, **kwargs)

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
            f'{form.instance.get_record_type_display()} of {form.instance.quantity} recorded.',
        )
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batch'] = self.batch
        ctx['title'] = 'Record mortality / cull'
        return ctx
