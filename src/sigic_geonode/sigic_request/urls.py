from django.urls import path, re_path

from sigic_geonode.sigic_request.request import RequestViewSet

urlpatterns = [
    path("/", RequestViewSet.as_view({"get": "list","post": "create"}), name="requests"),
    path("/<int:pk>", RequestViewSet.as_view({"get": "retrieve","put": "update", "patch": "partial_update"}), name="request"),
]
