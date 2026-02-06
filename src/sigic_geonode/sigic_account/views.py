from django.apps import apps
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeProfileSerializer


class MeProfileView(APIView):
    """
    Backend de 'Mi cuenta -> Información personal'
    Opera exclusivamente sobre request.user
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = MeProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class MeAvatarView(APIView):
    """
    Sube / reemplaza el avatar del usuario autenticado.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        Espera multipart/form-data con:
        - image: archivo
        """
        uploaded = request.FILES.get("image")
        if not uploaded:
            return Response(
                {"detail": "Falta el archivo 'image'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Avatar = apps.get_model("avatar", "Avatar")

        # Desmarcar primarios anteriores (si ququeremos que solo exista un primary)
        Avatar.objects.filter(user=request.user, primary=True).update(primary=False)

        avatar = Avatar.objects.create(
            user=request.user,
            avatar=uploaded,
            primary=True,
        )

        # Reutilizamos el serializer para regresar avatar_url actualizado
        serializer = MeProfileSerializer(request.user, context={"request": request})
        return Response(
            {
                "success": True,
                "avatar_id": avatar.id,
                "avatar_url": serializer.data.get("avatar_url"),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        """
        elimina avatar primary.
        """
        Avatar = apps.get_model("avatar", "Avatar")
        avatar = (
            Avatar.objects.filter(user=request.user, primary=True)
            .order_by("-id")
            .first()
        )
        if not avatar:
            return Response(
                {"detail": "No hay avatar primary."}, status=status.HTTP_404_NOT_FOUND
            )

        avatar.delete()
        serializer = MeProfileSerializer(request.user, context={"request": request})
        return Response(
            {"success": True, "avatar_url": serializer.data.get("avatar_url")}
        )
