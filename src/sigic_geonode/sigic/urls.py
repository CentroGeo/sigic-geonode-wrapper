from django.urls import path, include
from .viewsets import LinkWebSiteViewSet
from .router import drf_router

drf_router.register(r'sigic/link-web-site', LinkWebSiteViewSet, basename='link-web-site')
urlpatterns = drf_router.urls
