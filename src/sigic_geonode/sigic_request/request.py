import logging

from rest_framework import viewsets, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from .models import Request as SigicRequest
from .serializers import RequestSerializer
from geonode.base.api.pagination import GeoNodeApiPagination

logger = logging.getLogger(__name__)



class RequestViewSet(viewsets.ModelViewSet):
    
    serializer_class = RequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    #pagination_class = GeoNodeApiPagination

    # que solo el usuario admin pueda ver todas las solicitudes
    # y los usuarios normales solo las suyas
    def get_queryset(self):
        if self.request.user.is_superuser:
            return SigicRequest.objects.all()
        
        return SigicRequest.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        # asignar el usuario que hace la solicitud como owner
        serializer.save(owner=self.request.user)

