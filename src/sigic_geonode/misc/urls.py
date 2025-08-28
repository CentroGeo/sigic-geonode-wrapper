from .router import drf_router
from .viewsets import LinkWebSiteViewSet

drf_router.register(r"misc/link-web-site", LinkWebSiteViewSet, basename="link-web-site")
urlpatterns = drf_router.urls
