from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from core.access import ManagementRequiredMixin
from core.models import FeedType
from core.views import AuditFormMixin, BatchRecordDeleteView, BatchRecordUpdateView
from inventory.models import Batch

from .forms import FeedConsumptionForm, FeedPurchaseForm
from .models import (
    LOW_STOCK_THRESHOLD_KG,
    FeedConsumption,
    FeedPurchase,
    feed_stock_level,
)


class FeedStockView(LoginRequiredMixin, TemplateView):
    """Feed overview: stock level per feed type (with low-stock flag) plus
    recent purchases and consumption. All roles can view."""

    template_name = 'feed/feed_stock.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        stock = []
        for ft in FeedType.objects.all():
            level = feed_stock_level(ft)
            stock.append({
                'feed_type': ft,
                'level': level,
                'low': level <= LOW_STOCK_THRESHOLD_KG,
            })
        ctx['stock'] = stock
        ctx['threshold'] = LOW_STOCK_THRESHOLD_KG
        ctx['recent_purchases'] = FeedPurchase.objects.select_related('feed_type')[:10]
        ctx['recent_consumption'] = (
            FeedConsumption.objects.select_related('feed_type', 'batch')[:10]
        )
        user = self.request.user
        can_manage = user.is_superuser or user.role in ('OWNER', 'MANAGER')
        ctx['can_manage'] = can_manage
        actions = [''] if can_manage else []
        ctx['purchase_headers'] = ['Date', 'Feed type', 'Quantity', 'Total cost'] + actions
        ctx['consumption_headers'] = ['Date', 'Batch', 'Feed type', 'Qty (kg)'] + actions
        return ctx


class FeedPurchaseListView(LoginRequiredMixin, ListView):
    model = FeedPurchase
    template_name = 'feed/purchase_list.html'
    context_object_name = 'purchases'

    def get_queryset(self):
        return super().get_queryset().select_related('feed_type')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        can_manage = user.is_superuser or user.role in ('OWNER', 'MANAGER')
        ctx['can_manage'] = can_manage
        headers = ['Date', 'Feed type', 'Quantity', 'Unit cost', 'Total', 'Supplier']
        if can_manage:
            headers.append('')
        ctx['headers'] = headers
        return ctx


class FeedPurchaseCreateView(ManagementRequiredMixin, AuditFormMixin, CreateView):
    model = FeedPurchase
    form_class = FeedPurchaseForm
    template_name = 'feed/purchase_form.html'
    success_url = reverse_lazy('feed_purchase_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Feed purchase recorded; expense of {self.object.total_cost} posted to finance.',
        )
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Record feed purchase'
        return ctx


class FeedPurchaseUpdateView(ManagementRequiredMixin, AuditFormMixin, UpdateView):
    model = FeedPurchase
    form_class = FeedPurchaseForm
    template_name = 'feed/purchase_form.html'
    success_url = reverse_lazy('feed_purchase_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Feed purchase updated; finance expense re-synced to {self.object.total_cost}.',
        )
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit feed purchase'
        return ctx


class FeedPurchaseDeleteView(ManagementRequiredMixin, DeleteView):
    model = FeedPurchase
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('feed_purchase_list')

    def form_valid(self, form):
        messages.success(self.request, 'Feed purchase deleted; its finance expense was removed.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Delete feed purchase'
        ctx['cancel_url'] = reverse('feed_purchase_list')
        ctx['warning'] = ('The linked feed expense will also be removed, and this '
                          "reduces recorded stock for this feed type.")
        return ctx


class FeedConsumptionUpdateView(BatchRecordUpdateView):
    model = FeedConsumption
    form_class = FeedConsumptionForm
    template_name = 'feed/consumption_form.html'
    verbose = 'feed consumption'


class FeedConsumptionDeleteView(BatchRecordDeleteView):
    model = FeedConsumption
    verbose = 'feed consumption'


class FeedConsumptionCreateView(LoginRequiredMixin, AuditFormMixin, CreateView):
    """Daily consumption entry — attendant-accessible; batch from URL."""

    model = FeedConsumption
    form_class = FeedConsumptionForm
    template_name = 'feed/consumption_form.html'

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
        messages.success(self.request, 'Feed consumption recorded.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batch'] = self.batch
        ctx['title'] = 'Record feed consumption'
        return ctx
