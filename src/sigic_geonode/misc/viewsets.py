from rest_framework import viewsets
from .serializers import LinkWebSiteSerializer
from .models import LinkWebSite

class LinkWebSiteViewSet(viewsets.ModelViewSet):
    serializer_class = LinkWebSiteSerializer
    pagination_class = None
    queryset = LinkWebSite.objects.all()
