from django.urls import path

from sigic_geonode.sigic_request.request import Test

urlpatterns = [
    path("/test", Test.as_view(), name="test"),
]
