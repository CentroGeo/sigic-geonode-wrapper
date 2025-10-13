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
import logging
import os

import requests
from celery import Celery
from geonode.base import enumerations
from geonode.layers.models import Dataset
from requests.auth import HTTPBasicAuth

from sigic_geonode.sigic_georeference.utils import get_dataset, get_name_from_ds

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sigic_geonode.settings")

app = Celery("sigic_geonode")

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, name="sigic_geonode.debug_task", queue="default")
def debug_task(self):
    print("Request: {!r}".format(self.request))


def set_dataset_failed(ds: Dataset):
    ds.state = enumerations.STATE_INVALID
    ds.save()


@app.task(
    bind=True,
    name="sigic_geonode.sync_geoserver",
    queue="sigic_geonode.sync_geoserver",
    max_retries=5,
    on_failure=set_dataset_failed,
)
def sync_geoserver(self, layer_id: int):
    gs_server = os.getenv("GEOSERVER_LOCATION", "")
    url = (
        f"{gs_server}rest/workspaces/geonode/datastores/sigic_geonode_data/featuretypes"
    )

    ds = get_dataset(layer_id)
    if ds.state not in [enumerations.STATE_WAITING, enumerations.STATE_INVALID]:
        return {"status": "failed", "msg": "Dataset not in valid state"}
    layer = get_name_from_ds(ds)

    try:
        # Obtener los datos actuales para sobrescribir
        response = requests.get(
            f"{url}/{layer}.json",
            auth=HTTPBasicAuth(
                username=os.getenv("GEOSERVER_ADMIN_USER", ""),
                password=os.getenv("GEOSERVER_ADMIN_PASSWORD", ""),
            ),
            timeout=15,
        )
        if response.status_code != 200:
            raise Exception(f"Geoserver did not respond with 200, dataset {ds.id}")

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
            raise Exception(f"Geoserver did not respond with 200, dataset {ds.id}")
    except Exception as e:
        ds.state = enumerations.STATE_INVALID
        ds.save()
        logger.warning(f"Dataset not in valid state, error: {ds.id} {e}")
        raise e

    ds.state = enumerations.STATE_PROCESSED
    ds.save()
    return {"status": "success"}
