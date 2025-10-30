from rest_framework import serializers
from .models import Request as SigicRequest
from dynamic_rest.serializers import DynamicModelSerializer




#serializer para el modelo Request, para listar y crear elementos
# metodos: POST, GET (list, retrieve)
class RequestSerializer(DynamicModelSerializer):

    owner_username = serializers.CharField(source='owner.username', read_only=True)
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True, default=None)
    resource_title = serializers.CharField(source='resource.title', read_only=True)
    class Meta:
        model= SigicRequest
        name="request"
        #solo esta permitido modificar el resource , por eso solo ese campo en  falta en read_only_fields
        fields = (
            "pk",
            "resource",
            "resource_title",
            "owner",
            "owner_username",
            "reviewer",
            "reviewer_username",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "resource_title",
            "owner",
            "owner_username",
            "reviewer", 
            "reviewer_username",
            "status",
            "created_at",
            "updated_at"
        )

# serializer para el modelo Request, para editar el campo en revisor y status
# metodos: PUT, PATCH
# en el viewset debe ajustarse para que solo los usuarios admin (o quien va a revisar ) puedan usar este serializer
class RequestReviewerSerializer(DynamicModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True, default=None)
    resource_title = serializers.CharField(source='resource.title', read_only=True)
    class Meta:
        model= SigicRequest
        name="request"
        #aca el admin-revisor solo  puede modificar el status y el revisor
        fields = (
            "pk",
            "resource",
            "resource_title",
            "owner",
            "owner_username",
            "reviewer",
            "reviewer_username",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "resource",
            "resource_title",
            "owner",
            "owner_username",
             
            "reviewer_username",
            
            "created_at",
            "updated_at"
        )
