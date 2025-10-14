# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from django.urls import path, include
from geonode.urls import urlpatterns as geonode_urlpatterns
from sigic_geonode.sigic_auth.debug import whoami

urlpatterns = [
    path("sigic/whoami", whoami),
    path("sigic/georeference", include("sigic_geonode.sigic_georeference.urls")),
    path("sigic/ia/mediauploads/", include("sigic_geonode.sigic_ia_media_uploads.urls")),
    path("sigic/request", include("sigic_geonode.sigic_request.urls")),
] + geonode_urlpatterns

