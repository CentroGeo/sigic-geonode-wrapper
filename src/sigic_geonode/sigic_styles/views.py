from geonode.layers.api.views import DatasetViewSet
from rest_framework.decorators import action
from rest_framework.response import Response


class SigicDatasetViewSet(DatasetViewSet):

    @action(detail=True, methods=["get"], url_path="ping")
    def ping(self, request, pk=None):
        return Response({"status": "ok"})