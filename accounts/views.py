from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from core.access import OwnerRequiredMixin

from .forms import (
    ProfileForm,
    StyledPasswordChangeForm,
    UserCreateForm,
    UserEditForm,
)
from .models import User


class AppLoginView(LoginView):
    """Login with success/failure flash messages (shown as app toasts).

    Django's LoginView is silent by default; we add a green 'welcome' toast on
    success and a red toast on bad credentials, matching the rest of the app.
    """

    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        name = self.request.user.get_short_name() or self.request.user.get_username()
        messages.success(self.request, f'Welcome back, {name}. You are logged in.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Incorrect username or password. Please try again.')
        return super().form_invalid(form)


class UserListView(OwnerRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    ordering = ('username',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['headers'] = ['Username', 'Name', 'Email', 'Role', 'Status', '']
        ctx['add_url'] = reverse_lazy('user_add')
        return ctx


class UserCreateView(OwnerRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User "{self.object.username}" created.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Add user'
        return ctx


class UserUpdateView(OwnerRequiredMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User "{self.object.username}" updated.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Edit user'
        return ctx


class UserToggleActiveView(OwnerRequiredMixin, View):
    """Deactivate / reactivate a user. POST only. Owners can't lock themselves out."""

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
        else:
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
            state = 'reactivated' if user.is_active else 'deactivated'
            messages.success(request, f'User "{user.username}" {state}.')
        return redirect('user_list')


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Profile updated.')
        return response


class PasswordChangeView(LoginRequiredMixin, View):
    template_name = 'accounts/password_change.html'

    def get(self, request):
        return render(request, self.template_name,
                      {'form': StyledPasswordChangeForm(request.user)})

    def post(self, request):
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep the user logged in
            messages.success(request, 'Password changed.')
            return redirect('profile')
        return render(request, self.template_name, {'form': form})
