"""Admin-only routes check the role stored in the DB, never the token claim (NFR-10)."""

from rest_framework.permissions import BasePermission

from users.models import Role


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )
