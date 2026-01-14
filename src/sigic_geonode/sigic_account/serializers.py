from django.apps import apps
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

    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, user):
        """
        Devuelve URL absoluta del avatar primary del usuario, si existe.
        Usa la app 'avatar' instalada en GeoNode (django-avatar).
        """
        Avatar = apps.get_model("avatar", "Avatar")

        avatar = (
            Avatar.objects.filter(user=user, primary=True).order_by("-id").first()
        ) or (Avatar.objects.filter(user=user).order_by("-id").first())

        if not avatar or not getattr(avatar, "avatar", None):
            return None

        request = self.context.get("request")
        url = avatar.avatar.url  # esto ya trae MEDIA_URL + path
        return request.build_absolute_uri(url) if request else url

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
            "avatar_url",
        )
        read_only_fields = ("email", "avatar_url")
