import os
import requests
import typing
from contextlib import contextmanager

from uuid import uuid4
from pathlib import Path
from datetime import date
from importlib import import_module
from functools import lru_cache
from dataclasses import dataclass, field

from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.http import HttpRequest
from django.utils.text import slugify

from geonode.harvesting.resourcedescriptor import RecordDescription, RecordIdentification, RecordDistribution
from geonode.harvesting.harvesters.base import BaseHarvesterWorker
from geonode.resource.manager import resource_manager
from geonode.layers.models import Dataset
from geonode.base.auth import get_or_create_token

from importer.api.views import ImporterViewSet

engine = import_module(settings.SESSION_ENGINE)

PLACEHOLDER_SPATIAL_EXTENT = Polygon(((-180, -90),(-180, 90),(180, 90),(180, -90),(-180, -90)))

@dataclass()
class FileRemoteData:
    unique_identifier: str
    title: str
    resource_type: str
    url: str
    abstract: str = ""
    should_be_harvested: bool = False

@dataclass()
class FileDataInfo:
    resource_descriptor: RecordDescription
    additional_information: typing.Any | None
    copied_resources: typing.List[typing.Any] | None = field(default_factory=list)

class FileHarvester(BaseHarvesterWorker):
    http_session: requests.Session

    def __init__(self, remote_url: str, harvester_id: int):
        super().__init__(remote_url, harvester_id)
        self.name = slugify(remote_url)
        self.title = self.name
        self.url = remote_url
        self.uuid = str(uuid4())
        self.http_session = requests.Session()

    def allows_copying_resources(self):
        return False

    def get_geonode_resource_type(self, _):
        return Dataset

    @classmethod
    def from_django_record(cls, harvester: "Harvester"):
        return cls(remote_url=harvester.remote_url, harvester_id=harvester.id)

    def get_num_available_resources(self):
        # TODO Agregar funcionalidad en caso de tener archivos zip
        return 1

    def list_resources(self, offset = 0):
        # TODO Agregar funcionalidad en caso de tener archivos zip
        return [
            FileRemoteData(
                unique_identifier = self.uuid,
                title = self.title,
                resource_type = "File",
                url = self.url
            )
        ]

    def check_availability(self, timeout_seconds = 5):
        # TODO Agregar ping para revisar que si hay servidor
        return True

    def get_resource(self, harvestable_resource: "HarvestableResource"):
        return FileDataInfo(
            resource_descriptor=RecordDescription(
                uuid=harvestable_resource.unique_identifier,
                identification=RecordIdentification(
                    # TODO Name según valores entrada
                    name=self.name,
                    # TODO Title según valores entrada
                    title=self.title,
                    date=str(date.today()),
                    date_type="upload",
                    # TODO Abstract según valores entrada
                    abstract="",
                    # TODO Purpose según valores entrada
                    purpose="",
                    spatial_extent=PLACEHOLDER_SPATIAL_EXTENT,
                    other_constraints="",
                    other_keywords=[],
                    supplemental_information="",
                ),
                # TODO Language según valores entrada
                language="spa",
                data_quality="",
                distribution=RecordDistribution(
                    link_url=self.url,
                    thumbnail_url=None,
                ),
                reference_systems=["EPSG:4326"],
                additional_parameters={},
            ),
            additional_information=None,
            copied_resources=None,
        )

    def update_geonode_resource(self, harvested_info: FileDataInfo, harvestable_resource: "HarvestableResource"):
        defaults = self.get_geonode_resource_defaults(harvested_info, harvestable_resource)
        geonode_resource = harvestable_resource.geonode_resource
        if geonode_resource is None:
            geonode_resource_type = self.get_geonode_resource_type(harvestable_resource.remote_resource_type)
            geonode_resource = self._create_new_geonode_resource(geonode_resource_type, defaults)
        elif not geonode_resource.uuid == str(harvested_info.resource_descriptor.uuid):
            raise RuntimeError(
                f"""Recurso {geonode_resource!r} ya existe localmente pero su
                UUID ({geonode_resource.uuid}) no concuerda con el recurso
                remoto que ya existe, UUID {harvested_info.resource_descriptor.uuid!r}"""
            )
        else:
            geonode_resource = self._update_existing_geonode_resource(geonode_resource, defaults)
        
        harvestable_resource.geonode_resource = geonode_resource
        harvestable_resource.save()

        geonode_resource = resource_manager.update(str(harvested_info.resource_descriptor.uuid))
        self.finalize_resource_update(geonode_resource, harvested_info, harvestable_resource)

    def get_geonode_resource_defaults(self, harvested_resource_info: FileDataInfo, harvestable_resource: "HarvestableResource"):
        defaults = {
            "owner": harvestable_resource.harvester.default_owner,
            "uuid": str(harvested_resource_info.resource_descriptor.uuid),
            "abstract": harvested_resource_info.resource_descriptor.identification.abstract,
            "bbox_polygon": harvested_resource_info.resource_descriptor.identification.spatial_extent,
            "srid": harvested_resource_info.resource_descriptor.reference_systems[0],
            "constraints_other": harvested_resource_info.resource_descriptor.identification.other_constraints,
            "data_quality_statement": harvested_resource_info.resource_descriptor.data_quality,
            "date": harvested_resource_info.resource_descriptor.identification.date,
            "date_type": harvested_resource_info.resource_descriptor.identification.date_type,
            "language": harvested_resource_info.resource_descriptor.language,
            "purpose": harvested_resource_info.resource_descriptor.identification.purpose,
            "supplemental_information": (harvested_resource_info.resource_descriptor.identification.supplemental_information),
            "title": harvested_resource_info.resource_descriptor.identification.title,
            "thumbnail_url": harvested_resource_info.resource_descriptor.distribution.thumbnail_url,
        }
        defaults["name"] = harvested_resource_info.resource_descriptor.identification.name
        defaults.update(harvested_resource_info.resource_descriptor.additional_parameters)
        return defaults

    def _create_new_geonode_resource(self, geonode_resource_type, defaults):
        target_name = slugify(self.url)+".csv"
        with download_to_geonode(self.url, target_name=target_name) as file:
            create_from_importer(defaults, file)
        geonode_resource = resource_manager.search({"title": defaults["title"], "state": "PROCESSED"}, resource_type=geonode_resource_type).first()

        return geonode_resource

    def _update_existing_geonode_resource(self, geonode_resource, defaults):
        return geonode_resource

@lru_cache
def FileParser(url: str):
    target_name = slugify(url)
    fn = os.getcwd()+"/"+target_name+".csv"
    return fn

@contextmanager
def download_to_geonode(url: str, target_name: str):
    query_params = {"downloadformat": "csv"}
    response = requests.get(url, params=query_params)
    fn = os.getcwd()+"/"+target_name
    file_size = response.headers.get("Content-Length")
    content_type = response.headers.get("Content-Type")
    charset = response.apparent_encoding
    with open(fn, mode="wb+") as file:
        file.write(response.content)
    path = Path(fn)

    with open(fn, mode="rb") as file:
        uploaded_file = UploadedFile(open(fn, mode="rb"), path.name, content_type=content_type, size=file_size, charset=charset)
        yield uploaded_file

def create_from_importer(defaults, file):
    request = HttpRequest()
    request.method = "POST"
    request.user = defaults["owner"]
    request.session = engine.SessionStore()
    request.session["access_token"] = get_or_create_token(defaults["owner"])
    request.data = {
        "base_file": file,
        "action": "upload",
        "override_existing_layer": True,
    }
    request.headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "multipart/form-data",
    }
    request.FILES = {
        "base_file": file
    }
    request.session.save()
    importer = ImporterViewSet(request=request)
    importer.create(request)

