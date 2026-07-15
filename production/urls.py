from django.urls import path

from . import views

urlpatterns = [
    path('flocks/<int:batch_pk>/production/add/',
         views.ProductionEntryView.as_view(), name='production_add'),
    path('production/eggs/<int:pk>/edit/',
         views.EggProductionUpdateView.as_view(), name='egg_edit'),
    path('production/eggs/<int:pk>/delete/',
         views.EggProductionDeleteView.as_view(), name='egg_delete'),
    path('production/weight/<int:pk>/edit/',
         views.WeightRecordUpdateView.as_view(), name='weight_edit'),
    path('production/weight/<int:pk>/delete/',
         views.WeightRecordDeleteView.as_view(), name='weight_delete'),
]
