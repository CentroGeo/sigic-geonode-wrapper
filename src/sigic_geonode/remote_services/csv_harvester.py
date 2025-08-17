import os
import io
import requests
import typing
import logging
from functools import lru_cache
from dataclasses import dataclass, field
from uuid import uuid4
from datetime import date
from importlib import import_module
from pathlib import Path

from django.utils.text import slugify
from django.core.files import uploadedfile
from django.core.files.uploadedfile import UploadedFile
from django.contrib.gis.geos import Polygon
from django.conf import settings
from django.http import HttpRequest

from geonode.harvesting.resourcedescriptor import RecordDescription, RecordIdentification, RecordDistribution
from geonode.harvesting.harvesters.base import BaseHarvesterWorker, download_resource_file
from geonode.harvesting import config
from geonode.resource.manager import resource_manager
from geonode.storage.manager import storage_manager
from geonode.layers.models import Dataset
from geonode.base.auth import get_or_create_token

from importer.api.views import ImporterViewSet
engine = import_module(settings.SESSION_ENGINE)
logger = logging.getLogger(__name__)

@dataclass()
class CSVRemoteData:
    unique_identifier: str
    title: str
    resource_type: str
    url: str
    abstract: str = ""
    should_be_harvested: bool = False

@dataclass()
class CSVDataInfo:
    resource_descriptor: RecordDescription
    additional_information: typing.Any | None
    copied_resources: typing.List[typing.Any] | None = field(default_factory=list)

class CSVHarvester(BaseHarvesterWorker):
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
        # inicializar desde record de django
        return cls(remote_url=harvester.remote_url, harvester_id=harvester.id)

    def get_num_available_resources(self):
        # Regresar cuantos recursos
        return 1

    def list_resources(self, offset = 0):
        # regresar lista de recursos
        return [
            CSVRemoteData(
                unique_identifier = self.uuid,
                title = self.title,
                resource_type = "CSV",
                url = self.url
            )
        ]

    def check_availability(self, timeout_seconds = 5):
        return True

    def get_resource(self, harvestable_resource: "HarvestableResource"):
        return CSVDataInfo(
            resource_descriptor=RecordDescription(
                uuid=harvestable_resource.unique_identifier,
                identification=RecordIdentification(
                    name=self.name,
                    title=self.title,
                    date=str(date.today()),
                    date_type="upload",
                    abstract="",
                    purpose="",
                    # TODO Extremos de datos geo
                    spatial_extent=Polygon(
                        ((-122.19, 12.1),(-122.19, 32.72),(-84.64, 32.72),(-84.64, 12.1),(-122.19, 12.1))
                    ),
                    other_constraints="",
                    other_keywords=[],
                    supplemental_information="",
                ),
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

    def update_geonode_resource(self, harvested_info: CSVDataInfo, harvestable_resource: "HarvestableResource"):
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
        
        # with transaction.atomic():
        #     geoserver_resource = GeoServerResourceManager().create(
        #         defaults["uuid"],
        #         resource_type=geonode_resource_type,
        #         defaults=defaults,
        #     )
        #     geoserver_resource.save(notify=False)
        #     geonode_resource.save(notify=False)
        harvestable_resource.geonode_resource = geonode_resource
        harvestable_resource.save()

        geonode_resource = resource_manager.update(str(harvested_info.resource_descriptor.uuid))
        self.finalize_resource_update(geonode_resource, harvested_info, harvestable_resource)

    def get_geonode_resource_defaults(self, harvested_resource_info: CSVDataInfo, harvestable_resource: "HarvestableResource"):
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
        # return {key: value for key, value in defaults.items() if value is not None}
        return defaults

    def _create_new_geonode_resource(self, geonode_resource_type, defaults):
        # file_path = download_resource_file(self.url, target_name=self.name+".csv")
        file = download_to_geonode(self.url, target_name=os.getenv("MEDIA_ROOT")+self.name+".csv")
        setup_importer(defaults, file)

        geonode_resource = resource_manager.create(
            defaults["uuid"],
            resource_type=geonode_resource_type,
            defaults=defaults,
        )
        return geonode_resource

    def _update_existing_geonode_resource(self, geonode_resource, defaults):
        geonode_resource = resource_manager.update(
            self.harvester_id,
            instance=geonode_resource,
            vals=defaults,
        )
        return geonode_resource

@lru_cache
def CSVParser(url: str):
    target_name = slugify(url)
    fn = os.getcwd()+"/"+target_name+".csv"
    return fn

def download_to_geonode(url: str, target_name: str):
    # query_params = {"downloadformat": "csv"}
    # response = requests.get(url, params=query_params)
    # response.raise_for_status()
    # file_size = response.headers.get("Content-Length")
    # content_type = response.headers.get("Content-Type")
    # charset = response.apparent_encoding
    # size_threshold = config.get_setting("HARVESTED_RESOURCE_FILE_MAX_MEMORY_SIZE")
    # if file_size is not None and int(file_size) < size_threshold:
    #     logger.debug("Downloading to an in-memory buffer...")
    #     buf = io.BytesIO()
    #     file_ = uploadedfile.InMemoryUploadedFile(buf, None, target_name, content_type, file_size, charset)
    # else:
    #     logger.debug("Downloading to a temporary file...")
    #     file_ = uploadedfile.TemporaryUploadedFile(target_name, content_type, file_size, charset)
    # return file_

    query_params = {"downloadformat": "csv"}
    response = requests.get(url, params=query_params)
    target_name = slugify(url)+".csv"
    fn = os.getcwd()+"/"+target_name
    file_size = response.headers.get("Content-Length")
    content_type = response.headers.get("Content-Type")
    charset = response.apparent_encoding
    with open(fn, mode="wb+") as file:
        file.write(response.content)
        file.read()
        if storage_manager.exists(target_name):
            storage_manager.delete(target_name)
        file_name = storage_manager.save(target_name, file)
        result = Path(storage_manager.path(file_name))
    return UploadedFile(open(result, mode="rb"), result.name, content_type=content_type, size=file_size, charset=charset)

def setup_importer(defaults, file):
    # logger = logging.getLogger(__name__)
    # files={
    #     "base_file": (defaults["files"].name, open(str(defaults["files"].absolute(), mode="rb"))),
    #     "charset": (None, "UTF-8"),
    #     "store_spatial_files": (None, True),
    #     "Time": (None, True),
    # }
    # cookies = {
    #     'JSESSIONID': '19C56F6CF3CFA0ABF5941441F1726D8D',
    #     'csrftoken': 'sBZLZzrdF5CTDwmhPw1zEJjBe9fcSp8q',
    #     'sessionid': 'h4zzq9w252q95puj340i5vtgpe6g073q',
    #     'tabstyle': 'html-tab',
    # }
    # headers = {
    #         'Accept': 'application/json, text/plain, */*',
    #         }
    # response = requests.post(
    #     reverse('ImporterViewSet'),
    #     files=files,
    #     cookies=cookies,
    #     headers=headers,
    # )
    # logger.error(str(response.request.data))
    # logger.error(str(response.headers))
    # logger.error(str(response.))
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

