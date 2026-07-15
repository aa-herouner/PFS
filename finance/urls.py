from django.urls import path

from . import views

urlpatterns = [
    path('finance/', views.TransactionListView.as_view(), name='transaction_list'),
    path('finance/add/', views.TransactionCreateView.as_view(), name='transaction_add'),
    path('finance/<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='transaction_edit'),
    path('finance/<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
    path('finance/profit-loss/', views.ProfitLossView.as_view(), name='profit_loss'),
]
