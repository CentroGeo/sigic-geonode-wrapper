from rest_framework.routers import DefaultRouter

from .views import SLDViewSet

router = DefaultRouter()


router.register(r"sigic/sld", SLDViewSet, basename="sigic-sld")

urlpatterns = router.urls
