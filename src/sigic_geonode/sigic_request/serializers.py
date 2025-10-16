from rest_framework import serializers
from .models import Request as SigicRequest

from geonode.base.models import ResourceBase


#una opcion es serializar el resource base y mostrarlo con algunos campos en la impresion de cada objeto request
class ResourceBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceBase
        fields = ["pk","title","uuid","owner","abstract","created","last_updated"]



#serializer para el modelo Request, para el usuario que crea la solicitud
# 
class RequestSerializer(serializers.ModelSerializer):
    #owner = serializers.StringRelatedField()
    #reviewer = serializers.StringRelatedField()
    #resource = ResourceBaseSerializer(read_only=True)

    owner_username = serializers.CharField(source='owner.username', read_only=True)
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True, default=None)
    resource_title = serializers.CharField(source='resource.title', read_only=True)
    class Meta:
        model= SigicRequest
        fields = ["pk","resource", "resource_title", "owner", "owner_username", "reviewer", "reviewer_username", "status", "created_at", "updated_at",]
        read_only_fields = ["resource_title","owner","owner_username","reviewer", "reviewer_username", "status","created_at", "updated_at"]



