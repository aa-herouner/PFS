from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView

from core.access import OwnerRequiredMixin
from core.views import (
    AuditFormMixin,
    BatchRecordDeleteView,
    BatchRecordUpdateView,
    ReferenceCreateView,
    ReferenceDeleteView,
    ReferenceListView,
    ReferenceUpdateView,
)
from inventory.models import Batch

from .forms import HealthRecordForm, VaccinationScheduleForm
from .models import HealthRecord, VaccinationSchedule
from .services import due_vaccinations


class HealthRecordCreateView(LoginRequiredMixin, AuditFormMixin, CreateView):
    """Health record entry — attendant-accessible; batch from URL."""

    model = HealthRecord
    form_class = HealthRecordForm
    template_name = 'health/health_form.html'

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
        msg = f'{form.instance.get_record_type_display()} recorded.'
        if form.instance.cost and form.instance.cost > 0:
            msg += f' Expense of {form.instance.cost} posted to finance.'
        messages.success(self.request, msg)
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batch'] = self.batch
        ctx['title'] = 'Record health / medication'
        return ctx


class HealthRecordUpdateView(BatchRecordUpdateView):
    model = HealthRecord
    form_class = HealthRecordForm
    template_name = 'health/health_form.html'
    verbose = 'health record'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['batch'] = self.object.batch  # filter vaccine choices to this batch
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit health / medication'
        return ctx


class HealthRecordDeleteView(BatchRecordDeleteView):
    model = HealthRecord
    verbose = 'health record'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.cost and self.object.cost > 0:
            ctx['warning'] = ('The linked expense of '
                              f'{self.object.cost} will also be removed from finance.')
        return ctx


class VaccinationsDueView(LoginRequiredMixin, TemplateView):
    """Farm-wide upcoming/overdue vaccinations across active batches."""

    template_name = 'health/vaccinations_due.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['alerts'] = due_vaccinations()
        return ctx


# --- VaccinationSchedule CRUD (owner-only reference data) -------------------
class ScheduleListView(ReferenceListView):
    model = VaccinationSchedule
    title = 'Vaccination schedule'
    columns = (
        ('Vaccine', 'vaccine_name'),
        ('Day of age', 'day_of_age'),
        ('Bird types', 'bird_type_display'),
        ('Breed', 'breed'),
    )
    add_url_name = 'schedule_add'
    edit_url_name = 'schedule_edit'
    delete_url_name = 'schedule_delete'


class ScheduleCreateView(ReferenceCreateView):
    model = VaccinationSchedule
    form_class = VaccinationScheduleForm
    title = 'Add schedule entry'
    success_url = reverse_lazy('schedule_list')


class ScheduleUpdateView(ReferenceUpdateView):
    model = VaccinationSchedule
    form_class = VaccinationScheduleForm
    title = 'Edit schedule entry'
    success_url = reverse_lazy('schedule_list')


class ScheduleDeleteView(ReferenceDeleteView):
    model = VaccinationSchedule
    success_url = reverse_lazy('schedule_list')
