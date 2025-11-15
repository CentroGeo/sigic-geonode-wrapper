from geonode.layers.api.views import DatasetViewSet


class SigicDatasetViewSet(DatasetViewSet):

    @action(detail=True, methods=["get"], url_path="ping")
    def ping(self, request, pk=None):
        return Response({"status": "ok"})