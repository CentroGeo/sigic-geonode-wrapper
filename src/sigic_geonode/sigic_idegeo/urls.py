
from django.contrib import admin
from django.urls import path,re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt

from idegeo.api import api
from idegeo import views


urlpatterns = [

    # base urls
    path('', views.index, name='home'),
    path("api/", api.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path("accounts/", include("django.contrib.auth.urls")),
    path("catalogo/", include("idegeo.catalog.layers.urls")),
    path("catalogo/mapas/", include("idegeo.catalog.maps.urls")),
    path("geovisor/api/", include("idegeo.geovisor.api_urls")),
    re_path("^geovisor/(?:.*)/?", include("idegeo.geovisor.urls")),
    path("geonode_models/", include("idegeo.GeonodeModels.urls")),
    path("cms/", include("idegeo.content_handler.urls")),
    path("documentos/", include("idegeo.documents.urls")),
    path("panoramas/", include("idegeo.mviewer.urls")),
    path("escenarios/", include("idegeo.escenas.urls")),
    path("tmapas/", include("idegeo.topic_maps.urls")),
    path("dashboard/", include(("idegeo.dashboard.urls","idegeo.dashboard"),namespace="dashboard")),
    path("ckupload/", include("idegeo.CKUpload.urls")),
    path('interfaz/', views.interface_create, name='interface_create'),
    path('interfaz/<id>/', views.config_interface, name='config_interface'),
    re_path("^gestor_capas/(?:.*)/?", include('idegeo.layers_admin.urls')),
    re_path("^geo_historias/(?:.*)/?", include('idegeo.geo_stories.urls')),
    path("mapas/api/", include('idegeo.idegeo_maps.api_urls')),
    re_path("^mapas/(?:.*)/?", include('idegeo.idegeo_maps.urls')),
    path("archivos/api/", include('idegeo.file_manager.api_urls')),
    re_path("^archivos/(?:.*)/?", include('idegeo.file_manager.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
