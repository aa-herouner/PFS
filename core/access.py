"""Role-based access control.

Roles (see accounts.User.Role):
  OWNER      – everything, incl. user management + reference data
  MANAGER    – full data entry + reports
  ATTENDANT  – create/view daily records only

Use `RoleRequiredMixin` on CBVs or `role_required(...)` on FBVs. Both require
authentication first and return 403 (not a redirect) for a logged-in user who
lacks the role, so the failure is explicit.
"""
from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

# Convenience role groupings. Kept as plain strings to match User.Role values.
OWNER = 'OWNER'
MANAGER = 'MANAGER'
ATTENDANT = 'ATTENDANT'

# Managers can do everything an attendant can; owners everything a manager can.
MANAGEMENT = (OWNER, MANAGER)
ALL_ROLES = (OWNER, MANAGER, ATTENDANT)


class RoleRequiredMixin(LoginRequiredMixin):
    """Restrict a class-based view to users whose role is in `allowed_roles`.

    Superusers always pass (so the created superuser can reach everything even
    before its role is set to OWNER).
    """

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not (request.user.is_superuser or request.user.role in self.allowed_roles):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)


class OwnerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (OWNER,)


class ManagementRequiredMixin(RoleRequiredMixin):
    allowed_roles = MANAGEMENT


def role_required(*allowed_roles):
    """Decorator form for function-based views."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login

                return redirect_to_login(request.get_full_path())
            if not (request.user.is_superuser or request.user.role in allowed_roles):
                raise PermissionDenied('You do not have permission to access this page.')
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
