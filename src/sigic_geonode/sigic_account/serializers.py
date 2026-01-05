from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class MeProfileSerializer(serializers.ModelSerializer):
    department = serializers.CharField(
        source="delivery",
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Laboratorio, Área o Departamento (temporal, usa delivery)",
    )

    state = serializers.CharField(
        source="area", required=False, allow_blank=True, allow_null=True
    )

    postal_code = serializers.CharField(
        source="zipcode", required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "organization",
            "department",
            "position",
            "city",
            "state",
            "postal_code",
            "country",
        )
        read_only_fields = ("email",)
