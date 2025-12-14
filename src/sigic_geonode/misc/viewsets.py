from rest_framework import viewsets

from .models import LinkWebSite
from .serializers import LinkWebSiteSerializer


class LinkWebSiteViewSet(viewsets.ModelViewSet):
    serializer_class = LinkWebSiteSerializer
    pagination_class = None
    queryset = LinkWebSite.objects.all()
