from django.urls import path, re_path

from sigic_geonode.sigic_request.request import Index, Request

urlpatterns = [
    path("/", Index.as_view(), name="requests"),
    re_path(r"^/(?P<requestid>[^/]+)", Request.as_view(), name="request"),
    # path("/test", Test.as_view(), name="test"),
    # path("/approval", Approval.as_view(), name="approval"),
    # path("/approval/pk", Test.as_view(), name="approval-detail"),
    # path("/publication", Publication.as_view(), name="publication"),
    # path("/publication/pk", Test.as_view(), name="publication-detail"),
]
