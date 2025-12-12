from django.core.exceptions import ValidationError
from geonode.services.models import Service


def patch_service_model():
    """
    Patch model-level uniqueness for GeoNode Service.
    No admin, no serializers, no API.
    """

    def validate_unique(self, exclude=None):
        errors = {}

        if self.owner is None:
            errors["owner"] = "Owner is required."

        if self.base_url and self.owner:
            qs = Service.objects.filter(
                base_url=self.base_url,
                owner=self.owner,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                errors["base_url"] = "This base URL already exists for this owner."

        if errors:
            raise ValidationError(errors)

    # Monkey-patch REAL del modelo
    Service.validate_unique = validate_unique
