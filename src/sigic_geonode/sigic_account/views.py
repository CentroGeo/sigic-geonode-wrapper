from rest_framework import status
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
        serializer = MeProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = MeProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
