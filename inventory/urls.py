from django.urls import path

from . import views

urlpatterns = [
    path('flocks/', views.BatchListView.as_view(), name='batch_list'),
    path('flocks/add/', views.BatchCreateView.as_view(), name='batch_add'),
    path('flocks/<int:pk>/', views.BatchDetailView.as_view(), name='batch_detail'),
    path('flocks/<int:pk>/edit/', views.BatchUpdateView.as_view(), name='batch_edit'),
    path('flocks/<int:pk>/status/', views.BatchStatusUpdateView.as_view(), name='batch_status'),
    path('flocks/<int:batch_pk>/mortality/add/',
         views.MortalityCreateView.as_view(), name='mortality_add'),
    path('mortality/<int:pk>/edit/',
         views.MortalityUpdateView.as_view(), name='mortality_edit'),
    path('mortality/<int:pk>/delete/',
         views.MortalityDeleteView.as_view(), name='mortality_delete'),
]
