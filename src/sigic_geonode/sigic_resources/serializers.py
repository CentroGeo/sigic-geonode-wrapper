from geonode.base.api.serializers import ResourceBaseSerializer
from geonode.base.models import ResourceBase


class SigicResourceShortSerializer(ResourceBaseSerializer):
    class Meta:
        model = ResourceBase
        # respusta custom
        fields = [
            "alternate",
            "abstract",
            "attribution",
            "extent",
            "embed_url",
            "uuid",
            "title",
            "is_approved",
            "category",
            "download_url",
            "download_urls",
            "keywords",
            "last_updated",
            "links",
            "owner",
            "pk",
            "resource_type",
            "sourcetype",
            "subtype",
            "thumbnail_url",
            "raw_abstract",
            "srid",
            "featured",
            "advertised",
            "is_published",
            "created",
            "date",
        ]
