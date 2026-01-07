from rest_framework import serializers
from .models import Request as SigicRequest
from dynamic_rest.serializers import DynamicModelSerializer
from django.conf import settings
from geonode.base.models import ResourceBase
from geonode.base.api.serializers import DownloadLinkField, ExtentBboxField, SimpleTopicCategorySerializer
from django.apps import apps


def get_users_model():
    model_string = settings.AUTH_USER_MODEL
    return apps.get_model(model_string)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_users_model()
        fields = ('pk', 'username', 'email')

class ResourceSerializer(serializers.ModelSerializer):
    category = SimpleTopicCategorySerializer(read_only=True, default=None)
    extent = ExtentBboxField(required=False)
    download_url = DownloadLinkField(read_only=True)
    class Meta:
        model = ResourceBase
        fields = (
            'pk',
            'title',
            'category',
            'resource_type',
            'is_published',
            'extent',
            'sourcetype',
            'download_url',
        )

#serializer para el modelo Request, para listar y crear elementos
# metodos: POST, GET (list, retrieve)
class RequestSerializer(DynamicModelSerializer):
    resource = ResourceSerializer(read_only=True)
    resource_pk = serializers.PrimaryKeyRelatedField(
        queryset=ResourceBase.objects.all(),
        source='resource',
        write_only=True
    )
    owner = UserSerializer(read_only=True)
    reviewer = UserSerializer(read_only=True, default=None)
    class Meta:
        model = SigicRequest
        name = "request"
        #solo esta permitido modificar el resource , por eso solo ese campo en  falta en read_only_fields y tambien se agrega resource_pk para asignarlo al crear
        fields = (
            "pk",
            "resource",
            "resource_pk",
            "owner",
            "reviewer",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "owner",
            "reviewer", 
            "status",
            "rejection_reason",
            "created_at",
            "updated_at"
        )

# serializer para el modelo Request, para editar el campo en revisor y status
# metodos: PUT, PATCH
# en el viewset debe ajustarse para que solo los usuarios admin (o quien va a revisar ) puedan usar este serializer
class RequestReviewerSerializer(DynamicModelSerializer):
    resource = ResourceSerializer(read_only=True)
    owner = UserSerializer(read_only=True)
    reviewer = UserSerializer(read_only=True, default=None)
    # reviewer_pk = serializers.PrimaryKeyRelatedField(
    #     queryset=get_users_model().objects.all(),
    #     source='reviewer',
    #     write_only=True,
    #     required=False,
    #     allow_null=True,
    # )
    class Meta:
        model = SigicRequest
        name = "request"
        #aca el admin-revisor solo  puede modificar el status y el revisor
        fields = (
            "pk",
            "resource",
            "owner",
            "reviewer",
            # "reviewer_pk",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "resource",
            "owner",
            "created_at",
            "updated_at"
        )
