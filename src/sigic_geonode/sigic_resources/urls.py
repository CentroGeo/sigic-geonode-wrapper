from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import SigicResourceBaseViewSet, SigicResourceShortViewSet

router = DefaultRouter()
router.register(
    r"sigic-resources", SigicResourceBaseViewSet, basename="sigic-resources"
)
router.register(
    r"sigic-resources-short",
    SigicResourceShortViewSet,
    basename="sigic-resources-short",
)
# la url :/api/v2/resources/ mantiene la lógica original de ResourceBaseViewSet
urlpatterns = [
    path("", include(router.urls)),
]
