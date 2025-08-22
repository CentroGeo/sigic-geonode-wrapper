from rest_framework import serializers
from .models import LinkWebSite


class LinkWebSiteSerializer(serializers.ModelSerializer):

    class Meta:
        model = LinkWebSite
        fields = "__all__"
