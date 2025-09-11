from django.urls import path

from sigic_geonode.sigic_georeference.table_operations import JoinDataframes, Reset

urlpatterns = [
    path("/join", JoinDataframes.as_view(), name="join-dataframes"),
    path("/reset", Reset.as_view(), name="reset"),
]
