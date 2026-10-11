"""Small helper to protect views by role."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Usage: @role_required("student")  or  @role_required("staff", "admin")
    Not logged in -> redirect to login. Wrong role -> 403 Forbidden.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied("You do not have access to this page.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
