from geonode.services.models import Service
# from geonode.services.serializers import ServiceSerializer
from rest_framework.exceptions import ValidationError


def apply_service_model_patch():
    """
    Runtime sync with wrapper migration:

    - DB: base_url is NOT unique
    - DB: unique constraint is (base_url, owner)

    This patch only removes Django-level unique validation that
    still comes from the core model definition.
    """

    field = Service._meta.get_field("base_url")

    # Disable Django ORM uniqueness validation
    field.unique = False
    field._unique = False


def patch_service_serializer_validation():
    def validate_base_url(self, value):
        user = self.context["request"].user

        if Service.objects.filter(base_url=value, owner=user).exists():
            raise ValidationError("You have already registered this service.")

        return value

    # ServiceSerializer.validate_base_url = validate_base_url
