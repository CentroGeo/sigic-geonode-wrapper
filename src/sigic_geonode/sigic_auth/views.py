# src/sigic_geonode/sigic_auth/views.py

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import SigicGroup, SigicRole, UserGroupRole
from .serializers import (
    SigicGroupSerializer,
    SigicRoleSerializer,
    UserGroupRoleSerializer,
    UserGroupRoleNestedSerializer, UserInvitationCreateSerializer,
)
from .permissions import IsGroupAdmin
from rest_framework.permissions import IsAuthenticated, OR

User = get_user_model()


class SigicGroupViewSet(viewsets.ModelViewSet):
    queryset = SigicGroup.objects.all()
    serializer_class = SigicGroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class SigicRoleViewSet(viewsets.ModelViewSet):
    queryset = SigicRole.objects.all()
    serializer_class = SigicRoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserGroupRoleViewSet(viewsets.ModelViewSet):
    queryset = UserGroupRole.objects.all()
    serializer_class = UserGroupRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def my_roles(self, request):
        """Devuelve los roles del usuario autenticado, agrupados por grupo."""
        qset = UserGroupRole.objects.filter(user=request.user)

        data = {}
        for ugr in qset:
            group_name = ugr.group.name
            data.setdefault(group_name, []).append(ugr.role.name)

        return Response(data)


class UserGroupRoleByUserViewSet(viewsets.ViewSet):
    """
    API limitada para Keycloak:
    /api/auth/user/{id}/group-roles/
    """

    permission_classes = [permissions.AllowAny]  # luego pondremos token interno

    def retrieve(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        qset = UserGroupRole.objects.filter(user=user)
        data = {}

        for ugr in qset:
            group = ugr.group.name
            data.setdefault(group, []).append(ugr.role.name)

        return Response({"groups": data})


class MyGroupRolesView(views.APIView):
    """
    Devuelve los roles del usuario autenticado basados en el token OIDC.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qset = UserGroupRole.objects.filter(user=user)

        data = {}
        for ugr in qset:
            group = ugr.group.name
            data.setdefault(group, []).append(ugr.role.name)

        return Response({"groups": data})


class UserGroupRolesByEmailView(views.APIView):
    """
    Devuelve los roles por grupo de un usuario específico, buscado por email.
    Para uso de administradores o admin de grupo.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, email):
        try:
            target = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        # SUPERADMIN → puede ver cualquier cosa
        if request.user.is_superuser:
            qset = UserGroupRole.objects.filter(user=target)

        else:
            # Filtrar SOLO por los grupos donde request.user es admin
            admin_groups = UserGroupRole.objects.filter(
                user=request.user,
                role__name="admin"
            ).values_list("group_id", flat=True)

            qset = UserGroupRole.objects.filter(
                user=target,
                group_id__in=admin_groups
            )

        data = {}
        for ugr in qset:
            group = ugr.group.name
            data.setdefault(group, []).append(ugr.role.name)

        return Response({
            "email": email,
            "groups": data
        })


class UserInvitationAcceptView(generics.GenericAPIView):
    permission_classes = []

    def get(self, request, token):
        try:
            invitation = Invitation.objects.get(token=token)
        except Invitation.DoesNotExist:
            return Response({"detail": "Invalid invitation."}, status=404)

        if invitation.is_expired():
            return Response({"detail": "Invitation has expired."}, status=400)

        # ¿Ya existe el usuario?
        try:
            user = User.objects.get(email=invitation.email)
            user_exists = True
        except User.DoesNotExist:
            user_exists = False

        if user_exists:
            # Asignar directamente roles + grupo
            for role in invitation.roles.all():
                UserGroupRole.objects.get_or_create(
                    user=user, group=invitation.group, role=role
                )

            invitation.accepted = True
            invitation.accepted_at = timezone.now()
            invitation.save()

            return Response({"detail": "Invitación aceptada. Roles asignados."})

        else:
            # Redirigir a Keycloak para registrarse
            # redirigir a /invitations/callback/?token=...
            kc_register = (
                f"{settings.SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER}/protocol/openid-connect/registrations"
                f"?client_id={settings.SOCIALACCOUNT_OIDC_CLIENT_ID}"
                f"&redirect_uri={settings.SITEURL}api/v2/auth/invitations/callback/?token={token}"
            )
            return redirect(kc_register)


class UserInvitationCallbackView(generics.GenericAPIView):
    permission_classes = []

    def get(self, request):
        token = request.GET.get("token")
        if not token:
            return Response({"detail": "Missing token."}, status=400)

        try:
            invitation = Invitation.objects.get(token=token)
        except Invitation.DoesNotExist:
            return Response({"detail": "Invalid invitation."}, status=404)

        if invitation.is_expired():
            return Response({"detail": "Invitation expired."}, status=400)

        # OIDC token de Keycloak (el usuario ya se autenticó)
        user = request.user  # gracias a middleware OIDC (si lo tienes)
        if not user.is_authenticated:
            return Response({"detail": "Not authenticated."}, status=401)

        # Asignar roles
        for role in invitation.roles.all():
            UserGroupRole.objects.get_or_create(
                user=user, group=invitation.group, role=role
            )

        invitation.accepted = True
        invitation.accepted_at = timezone.now()
        invitation.save()

        return Response({"detail": "Invitación completada. Roles asignados."})


class UserInvitationCreateView(generics.CreateAPIView):
    serializer_class = InvitationCreateSerializer
    permission_classes = [IsAuthenticated & (IsGroupAdmin | IsAuthenticated)]
    # Aclaración:
    # - superuser pasa con IsAuthenticated
    # - admin de grupo pasa con IsGroupAdmin
    # - user normal NO pasa porque no es admin del grupo

    def perform_create(self, serializer):
        invitation = serializer.save(issued_by=self.request.user)
        send_invitation_email(invitation)


class AssignRolesToUserView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def post(self, request, group_id):
        email = request.data.get("email")
        roles = request.data.get("roles", [])

        if not email or not roles:
            return Response({"detail": "email y roles requeridos"}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        group = SigicGroup.objects.get(id=group_id)

        for role_name in roles:
            try:
                role = SigicRole.objects.get(name=role_name)
            except SigicRole.DoesNotExist:
                return Response({"detail": f"Role {role_name} no existe"}, status=400)

            UserGroupRole.objects.get_or_create(
                user=user,
                group=group,
                role=role
            )

        return Response({"detail": "Roles asignados"})


class RemoveRoleFromUserView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def delete(self, request, group_id):
        email = request.data.get("email")
        role_name = request.data.get("role")

        user = User.objects.get(email=email)
        role = SigicRole.objects.get(name=role_name)

        UserGroupRole.objects.filter(
            user=user,
            group_id=group_id,
            role=role
        ).delete()

        return Response({"detail": "Rol revocado"})