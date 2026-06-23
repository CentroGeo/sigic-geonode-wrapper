import logging
from dynamic_rest.viewsets import DynamicModelViewSet
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from geonode.base.api.pagination import GeoNodeApiPagination
from geonode.resource.manager import resource_manager
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

    def create(self, request, *args, **kwargs):
        resource_pk = request.data.get('resource_pk')
        if resource_pk:
            # Verificar si ya existe una solicitud para este recurso
            existing_request = SigicRequests.objects.filter(resource_id=resource_pk).first()
            if existing_request:
                # Verificar que el usuario actual es el dueño o superusuario
                if existing_request.owner != request.user and not request.user.is_superuser:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("No autorizado para modificar esta solicitud.")
                
                # Actualizar la solicitud existente en lugar de crear una nueva
                existing_request.status = 'pending'
                existing_request.reviewer = None
                existing_request.rejection_reason = None
                existing_request.save()
                
                # También nos aseguramos de que el recurso no esté publicado ni aprobado hasta que se verifique
                recurso = existing_request.resource
                recurso.is_published = False
                recurso.is_approved = False
                recurso.save()
                
                # Devolver la respuesta serializada
                serializer = self.get_serializer(existing_request)
                return Response(serializer.data)
                
        return super().create(request, *args, **kwargs)

    def revert_to_draft(self, request, *args, **kwargs):
        resource_pk = request.data.get('resource_pk')
        if not resource_pk:
            return Response({"error": "resource_pk es requerido."}, status=400)
        
        # 1. Obtener la capa (ResourceBase)
        from django.shortcuts import get_object_or_404
        recurso = get_object_or_404(ResourceBase, pk=resource_pk)
        
        # 2. Verificar que el usuario actual es el dueño de la capa o superusuario
        if recurso.owner != request.user and not request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No autorizado. Solo el propietario de la capa puede realizar esta acción.")
        
        # 3. Configurar el cambio de estatus de la capa en la base de datos (is_published y is_approved a False)
        recurso.is_published = False
        recurso.is_approved = False
        recurso.save()
        
        # 4. Cambiar el estatus de la solicitud a 'editing' (Borrador / En edición)
        requests_query = SigicRequests.objects.filter(resource=recurso)
        
        if requests_query.exists():
            # Actualizamos el estatus de las solicitudes existentes a 'editing'
            requests_query.update(status='editing', reviewer=None, rejection_reason=None)
        else:
            # Si por alguna razón no existía una solicitud, la creamos con estatus 'editing'
            SigicRequests.objects.create(
                resource=recurso,
                owner=recurso.owner,
                status='editing'
            )
            
        return Response({"success": True, "message": "La capa ha sido regresada a edición / borrador."})
    
    def reopen(self, request):

        resource_pk = request.data.get('resource_pk')

        solicitud = SigicRequests.objects.filter(resource_id=resource_pk, status='published').first()

        if not solicitud:
            raise ValidationError("No existe una solicitud publicada para este recurso.")

        # Corroborar identidad
        if solicitud.owner != request.user and not request.user.is_superuser:
            raise PermissionDenied("Solo el propietario puede volver a editar la capa.")

        geonode_resource = solicitud.resource

        # Sacar del catálogo
        perm_spec = {
            "users": {"AnonymousUser": []},
            "groups": {"anonymous": [], "registered-members": []},
        }
        resource_manager.set_permissions(
            geonode_resource.uuid,
            instance=geonode_resource,
            permissions=perm_spec,
            created=False
        )

        # Cambiar estatus
        geonode_resource.is_published = False
        geonode_resource.is_approved = False
        geonode_resource.save()

        # Eliminar la solicitud publicada para que inicie "desde cero"
        solicitud.delete()

        return Response({"detail": "Capa reabierta para edición.", "resource_pk": geonode_resource.pk})
    
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
