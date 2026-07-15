from django.urls import path

from . import views

urlpatterns = [
    path('settings/', views.SettingsView.as_view(), name='settings'),

    # Breeds
    path('settings/breeds/', views.BreedListView.as_view(), name='breed_list'),
    path('settings/breeds/add/', views.BreedCreateView.as_view(), name='breed_add'),
    path('settings/breeds/<int:pk>/edit/', views.BreedUpdateView.as_view(), name='breed_edit'),
    path('settings/breeds/<int:pk>/delete/', views.BreedDeleteView.as_view(), name='breed_delete'),

    # Pens
    path('settings/pens/', views.PenListView.as_view(), name='pen_list'),
    path('settings/pens/add/', views.PenCreateView.as_view(), name='pen_add'),
    path('settings/pens/<int:pk>/edit/', views.PenUpdateView.as_view(), name='pen_edit'),
    path('settings/pens/<int:pk>/delete/', views.PenDeleteView.as_view(), name='pen_delete'),

    # Feed types
    path('settings/feed-types/', views.FeedTypeListView.as_view(), name='feedtype_list'),
    path('settings/feed-types/add/', views.FeedTypeCreateView.as_view(), name='feedtype_add'),
    path('settings/feed-types/<int:pk>/edit/', views.FeedTypeUpdateView.as_view(), name='feedtype_edit'),
    path('settings/feed-types/<int:pk>/delete/', views.FeedTypeDeleteView.as_view(), name='feedtype_delete'),

    # Expense categories
    path('settings/expense-categories/', views.ExpenseCategoryListView.as_view(), name='expensecategory_list'),
    path('settings/expense-categories/add/', views.ExpenseCategoryCreateView.as_view(), name='expensecategory_add'),
    path('settings/expense-categories/<int:pk>/edit/', views.ExpenseCategoryUpdateView.as_view(), name='expensecategory_edit'),
    path('settings/expense-categories/<int:pk>/delete/', views.ExpenseCategoryDeleteView.as_view(), name='expensecategory_delete'),

    # Income categories
    path('settings/income-categories/', views.IncomeCategoryListView.as_view(), name='incomecategory_list'),
    path('settings/income-categories/add/', views.IncomeCategoryCreateView.as_view(), name='incomecategory_add'),
    path('settings/income-categories/<int:pk>/edit/', views.IncomeCategoryUpdateView.as_view(), name='incomecategory_edit'),
    path('settings/income-categories/<int:pk>/delete/', views.IncomeCategoryDeleteView.as_view(), name='incomecategory_delete'),
]
