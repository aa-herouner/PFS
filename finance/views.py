from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from core.access import ManagementRequiredMixin
from core.views import AuditFormMixin
from inventory.models import Batch

from .forms import TransactionForm
from .models import Transaction
from .services import (
    batch_profit_loss,
    expense_by_category,
    period_summary,
    totals,
)


class TransactionListView(ManagementRequiredMixin, ListView):
    model = Transaction
    template_name = 'finance/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'income_category', 'expense_category', 'batch')
        p = self.request.GET
        if p.get('type'):
            qs = qs.filter(type=p['type'])
        if p.get('source'):
            qs = qs.filter(source=p['source'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['totals'] = totals(self.get_queryset())
        ctx['types'] = Transaction.Type.choices
        ctx['sources'] = Transaction.Source.choices
        ctx['filters'] = {'type': self.request.GET.get('type', ''),
                          'source': self.request.GET.get('source', '')}
        ctx['table_headers'] = ['Date', 'Type', 'Category', 'Amount', 'Batch', 'Source', '']
        return ctx


class TransactionCreateView(ManagementRequiredMixin, AuditFormMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def get_initial(self):
        initial = super().get_initial()
        # The user picks Income/Expense before landing here (see the list page
        # popup); preselect it from the query string. Still editable on the form.
        chosen = self.request.GET.get('type')
        if chosen in Transaction.Type.values:
            initial['type'] = chosen
        return initial

    def form_valid(self, form):
        form.instance.source = Transaction.Source.MANUAL
        response = super().form_valid(form)
        messages.success(self.request, 'Transaction recorded.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        chosen = self.request.GET.get('type')
        if chosen == Transaction.Type.INCOME:
            ctx['title'] = 'Add income'
        elif chosen == Transaction.Type.EXPENSE:
            ctx['title'] = 'Add expense'
        else:
            ctx['title'] = 'Add transaction'
        return ctx


class ManualOnlyMixin:
    """Block editing/deleting auto-created (FEED/HEALTH) transactions."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.is_readonly:
            raise PermissionDenied('Auto-created transactions are edited at their source record.')
        return obj


class TransactionUpdateView(ManagementRequiredMixin, ManualOnlyMixin, AuditFormMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Transaction updated.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit transaction'
        return ctx


class TransactionDeleteView(ManagementRequiredMixin, ManualOnlyMixin, DeleteView):
    model = Transaction
    template_name = 'finance/transaction_confirm_delete.html'
    success_url = reverse_lazy('transaction_list')

    def form_valid(self, form):
        messages.success(self.request, 'Transaction deleted.')
        return super().form_valid(form)


class ProfitLossView(ManagementRequiredMixin, TemplateView):
    """Farm-wide P&L + per-batch breakdown + expense-by-category."""

    template_name = 'finance/profit_loss.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start = self.request.GET.get('start') or None
        end = self.request.GET.get('end') or None
        ctx['summary'] = period_summary(start, end)
        ctx['expense_categories'] = expense_by_category(start, end)
        ctx['batches'] = [
            {'batch': b, 'pl': batch_profit_loss(b)}
            for b in Batch.objects.select_related('breed')
        ]
        ctx['filters'] = {'start': start or '', 'end': end or ''}
        ctx['batch_headers'] = ['Batch', 'Income', 'Expense', 'Net', 'Cost/bird']
        return ctx
