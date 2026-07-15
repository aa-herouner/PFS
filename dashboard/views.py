from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from . import services


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['kpis'] = services.kpis()
        ctx['eggs_week_hint'] = f"this week: {ctx['kpis']['eggs_week']}"
        ctx['feed_stock'] = services.feed_stock_status()
        ctx['alerts'] = services.alerts()
        ctx['mortality_trend'] = services.mortality_trend()
        ctx['egg_trend'] = services.egg_production_trend()
        ctx['expense_breakdown'] = services.expense_breakdown()
        return ctx
