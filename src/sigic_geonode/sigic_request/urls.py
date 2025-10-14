from django.urls import path, re_path

from sigic_geonode.sigic_request.request import Index, Request

urlpatterns = [
    path("/", Index.as_view(), name="requests"),
    re_path(r"^/(?P<requestid>[^/]+)", Request.as_view(), name="request"),
]
