from django.urls import path
from sigic_geonode.sigic_requests.views import RequestsViewSet

urlpatterns = [
    path("/", RequestsViewSet.as_view({"get": "list","post": "create"}), name="requests"),
    path("/revert-to-draft", RequestsViewSet.as_view({"post": "revert_to_draft"}), name="request-revert-to-draft"),
    path("/reopen", RequestsViewSet.as_view({"post": "reopen"}), name="request-reopen"),
    path("/<int:pk>", RequestsViewSet.as_view({"get": "retrieve","put": "update", "patch": "partial_update"}), name="request"),
]
