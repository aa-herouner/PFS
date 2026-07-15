from django.urls import path

from . import views

urlpatterns = [
    # Owner-only user management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/add/', views.UserCreateView.as_view(), name='user_add'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/toggle/', views.UserToggleActiveView.as_view(), name='user_toggle'),

    # Self-service
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/password/', views.PasswordChangeView.as_view(), name='password_change_own'),
]
