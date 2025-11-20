# src/sigic_geonode/sigic_auth/permissions.py

from rest_framework.permissions import BasePermission
from .models import UserGroupRole, SigicRole


class IsGroupAdmin(BasePermission):
    """
    Permite acceso si el request.user es admin del grupo especificado.
    El grupo debe llegar por:
      - path kwarg: group_id
      - o por el cuerpo (POST)
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # 1. Si el usuario es superuser → dejarlo pasar
        if user.is_superuser or user.is_staff:
            return True

        group_id = (
            request.data.get("group") or
            getattr(view, "kwargs", {}).get("group_id")
        )

        if not group_id:
            return False  # no se puede validar

        try:
            admin_role = SigicRole.objects.get(name="admin")
        except SigicRole.DoesNotExist:
            return False

        return UserGroupRole.objects.filter(
            user=user,
            group_id=group_id,
            role=admin_role
        ).exists()
