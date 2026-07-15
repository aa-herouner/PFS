from django.urls import path

from . import views

urlpatterns = [
    path('reports/', views.ReportIndexView.as_view(), name='report_index'),
    path('reports/<slug:slug>/', views.ReportDetailView.as_view(), name='report_detail'),
]
