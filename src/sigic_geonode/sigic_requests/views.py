import logging
from dynamic_rest.viewsets import DynamicModelViewSet
from rest_framework import permissions
from rest_framework.response import Response
from geonode.base.api.pagination import GeoNodeApiPagination
from .models import Requests as SigicRequests
from geonode.base.models import ResourceBase
from .serializers import RequestsSerializer, RequestReviewerSerializer


logger = logging.getLogger(__name__)

class RequestsViewSet(DynamicModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = GeoNodeApiPagination

    # que solo el usuario admin pueda ver todas las solicitudes
    # y los usuarios normales solo las suyas
    def get_queryset(self):
        if self.request.user.is_superuser:
            return SigicRequests.objects.all()
        
        return SigicRequests.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        # asignar el usuario que hace la solicitud como owner
        serializer.save(owner=self.request.user)
    
    def perform_update(self, serializer):
        # no hacer si el usuario no es admin (o reviewer tambien luego)
        if not self.request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No autorizado para modificar esta solicitud.")
        id_recurso = serializer.instance.resource.id
        status_recibido = serializer.validated_data.get('status')
        print(f"Nuevo estado de la solicitud: {status_recibido}")
        publicar = serializer.validated_data.get('status') == 'published'
        print(f"Publicar recurso: {publicar}")
        serializer.save(reviewer=self.request.user)

        recurso = ResourceBase.objects.filter(id=id_recurso).first()
        recurso.is_published = publicar
        recurso.is_approved = publicar
        recurso.save()

        # Refrescar la instancia del recurso relacionado para que el serializer incluya los cambios
        serializer.instance.resource.refresh_from_db()

    # def update(self, request, *args, **kwargs):
    #     partial = kwargs.pop('partial', False)
    #     instance = self.get_object()
    #     serializer = self.get_serializer(instance, data=request.data, partial=partial)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_update(serializer)

    #     # Refrescar el serializer con la instancia actualizada para incluir cambios en el recurso relacionado
    #     serializer = self.get_serializer(instance)
    #     return Response(serializer.data)

    def get_serializer_class(self):
        # si el usuario es admin o revisor usar el serializer para reviewer
        # eso se define a partir de la accion que se esta realizando

        if self.action in ['update', 'partial_update']:
            return RequestReviewerSerializer
            # por ahora si no es admin no puede actualizar la solicitud
            
        return RequestsSerializer
