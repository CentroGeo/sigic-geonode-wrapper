import logging

from rest_framework import viewsets, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from .models import Request as SigicRequest
from .serializers import RequestSerializer, RequestReviewerSerializer
from geonode.base.api.pagination import GeoNodeApiPagination

logger = logging.getLogger(__name__)



class RequestViewSet(viewsets.ModelViewSet):
    
    
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
    
    def perform_update(self, serializer):
        # no hacer si el usuario no es admin (o reviewer tambien luego)
        if not self.request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No autorizado para modificar esta solicitud.")
        serializer.save()

    def get_serializer_class(self):
        # si el usuario es admin o revisor usar el serializer para reviewer
        # eso se define a partir de la accion que se esta realizando

        if self.action in ['update', 'partial_update']:
            return RequestReviewerSerializer
            # por ahora si no es admin no puede actualizar la solicitud
            
        return RequestSerializer

