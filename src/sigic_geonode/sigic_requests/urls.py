from django.urls import path
from sigic_geonode.sigic_requests.views import RequestsViewSet

urlpatterns = [
    path("/", RequestsViewSet.as_view({"get": "list","post": "create"}), name="requests"),
    path("/reopen", RequestsViewSet.as_view({"post": "reopen"}), name="request-reopen"),
    path("/<int:pk>", RequestsViewSet.as_view({"get": "retrieve","put": "update", "patch": "partial_update"}), name="request"),
]
