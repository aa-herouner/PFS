from django.urls import path

from . import views

urlpatterns = [
    path('flocks/<int:batch_pk>/health/add/',
         views.HealthRecordCreateView.as_view(), name='health_add'),
    path('health/<int:pk>/edit/',
         views.HealthRecordUpdateView.as_view(), name='health_edit'),
    path('health/<int:pk>/delete/',
         views.HealthRecordDeleteView.as_view(), name='health_delete'),
    path('health/vaccinations-due/',
         views.VaccinationsDueView.as_view(), name='vaccinations_due'),

    # Vaccination schedule (owner-only reference data)
    path('settings/vaccination-schedule/',
         views.ScheduleListView.as_view(), name='schedule_list'),
    path('settings/vaccination-schedule/add/',
         views.ScheduleCreateView.as_view(), name='schedule_add'),
    path('settings/vaccination-schedule/<int:pk>/edit/',
         views.ScheduleUpdateView.as_view(), name='schedule_edit'),
    path('settings/vaccination-schedule/<int:pk>/delete/',
         views.ScheduleDeleteView.as_view(), name='schedule_delete'),
]
