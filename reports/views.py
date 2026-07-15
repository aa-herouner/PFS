from django.http import Http404
from django.views.generic import TemplateView, View

from core.access import ManagementRequiredMixin

from .exporters import to_excel, to_pdf
from .services import REPORTS

REPORT_LABELS = {
    'batch-performance': 'Batch performance',
    'mortality': 'Mortality & culls',
    'feed': 'Feed usage',
    'production': 'Production',
    'financial': 'Financial (P&L)',
}


class ReportIndexView(ManagementRequiredMixin, TemplateView):
    template_name = 'reports/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reports'] = REPORT_LABELS
        return ctx


class ReportDetailView(ManagementRequiredMixin, View):
    """Render a report on screen, or export it as Excel/PDF via ?format=."""

    template_name = 'reports/report.html'

    def get(self, request, slug):
        builder = REPORTS.get(slug)
        if builder is None:
            raise Http404('Unknown report')
        start = request.GET.get('start') or None
        end = request.GET.get('end') or None
        report = builder(start, end)

        fmt = request.GET.get('format')
        if fmt == 'excel':
            return to_excel(report)
        if fmt == 'pdf':
            return to_pdf(report)

        from django.shortcuts import render
        return render(request, self.template_name, {
            'report': report, 'slug': slug,
            'filters': {'start': start or '', 'end': end or ''},
        })
