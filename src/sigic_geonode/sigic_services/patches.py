from geonode.services.models import Service
# from geonode.services.serializers import ServiceSerializer
from rest_framework.exceptions import ValidationError


def apply_service_model_patch():
    original_validate_unique = Service.validate_unique

    def patched_validate_unique(self, exclude=None):
        if exclude is None:
            exclude = ["base_url"]
        else:
            exclude = list(exclude) + ["base_url"]
        return original_validate_unique(self, exclude=exclude)

    Service.validate_unique = patched_validate_unique


def patch_service_serializer_validation():
    def validate_base_url(self, value):
        user = self.context["request"].user

        if Service.objects.filter(base_url=value, owner=user).exists():
            raise ValidationError("You have already registered this service.")

        return value

    # ServiceSerializer.validate_base_url = validate_base_url
