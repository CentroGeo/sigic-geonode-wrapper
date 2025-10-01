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

from __future__ import absolute_import

import json
import os
from time import sleep

import requests
from celery import Celery
from geonode.base import enumerations
from geonode.layers.models import Dataset
from requests.auth import HTTPBasicAuth
from rest_framework.response import Response

from sigic_geonode.sigic_georeference.utils import get_name_from_ds

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sigic_geonode.settings")

app = Celery("sigic_geonode")

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, name="sigic_geonode.debug_task", queue="default")
def debug_task(self):
    print("Request: {!r}".format(self.request))


@app.task(
    bind=True,
    name="sigic_geonode.sync_geoserver",
    queue="sigic_geonode.sync_geoserver",
    max_retries=5,
)
def sync_geoserver(self, layer_id: int):
    sleep(3)
    gs_server = os.getenv("GEOSERVER_LOCATION", "")
    url = (
        f"{gs_server}rest/workspaces/geonode/datastores/sigic_geonode_data/featuretypes"
    )

    ds: Dataset = Dataset.objects.filter(id=layer_id).first()
    layer = get_name_from_ds(ds)

    # Obtener los datos actuales para sobrescribir
    response = requests.get(
        f"{url}/{layer}.json",
        auth=HTTPBasicAuth(
            username=os.getenv("GEOSERVER_ADMIN_USER", ""),
            password=os.getenv("GEOSERVER_ADMIN_PASSWORD", ""),
        ),
        timeout=15,
    )

    # Enviar nuevos datos con commando de recalcular nativebbox/latlogbbox
    feature_types = response.json()
    feature_types["featureType"]["srs"] = ds.srid

    response = requests.put(
        f"{url}/{layer}.json?recalculate=nativebbox,latlonbbox",
        data=json.dumps(feature_types),
        auth=HTTPBasicAuth(
            username=os.getenv("GEOSERVER_ADMIN_USER", ""),
            password=os.getenv("GEOSERVER_ADMIN_PASSWORD", ""),
        ),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if response.status_code != 200:
        ds.state = enumerations.STATE_INVALID
        ds.save()
        return Response({"status": "failed"})
    ds.state = enumerations.STATE_PROCESSED
    ds.save()
    return Response({"status": "success"})
