# src/sigic_geonode/sigic_auth/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import SigicGroup, SigicRole, UserGroupRole, UserInvitation

User = get_user_model()


class SigicRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SigicRole
        fields = ["id", "name"]


class SigicGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SigicGroup
        fields = ["id", "name", "description"]


class UserGroupRoleSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    group = serializers.PrimaryKeyRelatedField(queryset=SigicGroup.objects.all())
    role = serializers.PrimaryKeyRelatedField(queryset=SigicRole.objects.all())

    class Meta:
        model = UserGroupRole
        fields = ["id", "user", "group", "role"]
        read_only_fields = ["id"]


class UserGroupRoleNestedSerializer(serializers.ModelSerializer):
    group = SigicGroupSerializer()
    role = SigicRoleSerializer()

    class Meta:
        model = UserGroupRole
        fields = ["group", "role"]


class UserInvitationCreateSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(
        queryset=SigicRole.objects.all(), many=True
    )

    class Meta:
        model = UserInvitation
        fields = ["email", "group", "roles"]

    def create(self, validated_data):
        roles = validated_data.pop("roles")
        invitation = UserInvitation.objects.create(**validated_data)
        invitation.roles.set(roles)
        return invitation

