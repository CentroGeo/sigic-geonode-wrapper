# from django.urls import include, path
# from rest_framework.routers import DefaultRouter

from sigic_geonode.router import router

from .views import SigicResourceBaseViewSet, SigicResourceShortViewSet

router.register(
    r"api/v2/sigic-resources", SigicResourceBaseViewSet, basename="sigic-resources"
)
router.register(
    r"api/v2/sigic-resources-short",
    SigicResourceShortViewSet,
    basename="sigic-resources-short",
)

# la url :/api/v2/resources/ mantiene la lógica original de ResourceBaseViewSet
urlpatterns = [
    # path("", include(router.urls)),
]
