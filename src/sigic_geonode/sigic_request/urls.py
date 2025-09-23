from django.urls import path

from sigic_geonode.sigic_request.request import Index, Approval, Test

urlpatterns = [
    path("/", Index.as_view(), name="index"),
    path("/test", Test.as_view(), name="test"),
    path("/approval", Approval.as_view(), name="approval"),
    # path("/approval/pk", Test.as_view(), name="approval-detail"),
    path("/publication", Test.as_view(), name="publication"),
    # path("/publication/pk", Test.as_view(), name="publication-detail"),
]
