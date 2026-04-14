from functools import wraps

from django.http import HttpResponseForbidden


def require_role(*roles):
    """
    View decorator that checks if the authenticated user's CoopMember
    has one of the specified roles.

    Usage:
        @require_role("admin")
        def admin_only_view(request): ...

        @require_role("admin", "member")
        def adults_only_view(request): ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from coop.models import CoopMember

            try:
                member = CoopMember.objects.get(
                    auth_user_id=request.auth_user.id
                )
            except CoopMember.DoesNotExist:
                return HttpResponseForbidden("Not a co-op member")

            if member.role not in roles:
                return HttpResponseForbidden("You don't have permission to view this page")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
