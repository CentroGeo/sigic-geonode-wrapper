import requests
import typing
from functools import lru_cache
from dataclasses import dataclass, field

from django.utils.text import slugify
from geonode.harvesting.resourcedescriptor import RecordDescription, RecordIdentification, RecordDistribution
from geonode.harvesting.harvesters.base import BaseHarvesterWorker
from geonode.layers.models import Dataset
from geonode.geoserver.manager import GeoServerResourceManager

gs_resource_manager = GeoServerResourceManager()

@dataclass()
class CSVRemoteData:
    unique_identifier: str
    title: str
    resource_type: str
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
        self.url = self.remote_url
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
                unique_identifier = self.url,
                title = self.title,
                resource_type = "CSV",
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
                    abstract="",
                    # TODO Extremos de datos geo
                    # spatial_extent=,
                    other_constraints="",
                    other_keywords=[],
                ),
                distribution=RecordDistribution(
                    link_url=harvestable_resource.unique_identifier,
                    thumbnail_url=None,
                ),
                reference_systems=[],
                additional_parameters={},
            ),
            additional_information=None,
            copied_resources=None,
        )

    def update_geonode_resource(self, harvested_resource_info: CSVDataInfo, harvestable_resource: "HarvestableResource"):
        defaults = self.get_geonode_resource_defaults(harvested_resource_info, harvestable_resource)
        geonode_resource = harvestable_resource.geonode_resource
        if geonode_resource is None:
            geonode_resource_type = self.get_geonode_resource_type(harvestable_resource.remote_resource_type)
            geonode_resource = self._create_new_geonode_resource(geonode_resource_type, defaults)
        elif not geonode_resource.uuid == str(harvested_resource_info.resource_descriptor.uuid):
            raise RuntimeError(
                f"""Recurso {geonode_resource!r} ya existe localmente pero su
                UUID ({geonode_resource.uuid}) no concuerda con el recurso
                remoto que ya existe, UUID {harvested_resource_info.resource_descriptor.uuid!r}"""
            )
        else:
            geonode_resource = self._update_existing_geonode_resource(geonode_resource, defaults)
        harvestable_resource.geonode_resource = geonode_resource
        harvestable_resource.save()

    def get_geonode_resource_defaults(self, harvested_resource_info: CSVDataInfo, harvestable_resource: "HarvestableResource"):
        defaults = {
            "owner": harvestable_resource.harvester.default_owner,
            "uuid": str(harvested_resource_info.resource_descriptor.uuid),
            "abstract": harvested_resource_info.resource_descriptor.identification.abstract,
            "bbox_polygon": harvested_resource_info.resource_descriptor.identification.spatial_extent,
            "constraints_other": harvested_resource_info.resource_descriptor.identification.other_constraints,
            "created": harvested_resource_info.resource_descriptor.date_stamp,
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
        defaults["files"] = [slugify(self.url)+".csv"]
        defaults.update(harvested_resource_info.resource_descriptor.additional_parameters)
        return defaults

    def _create_new_geonode_resource(self, geonode_resource_type, defaults):
        resource_files = defaults.get("files", [])
        DatasetManager.upload_files(resource_files)
        geonode_resource = ds_resource_manager.create(
            defaults["uuid"],
            resource_type=geonode_resource_type,
            defaults=defaults,
            resource_files,
            importer_session_opts={"name": defaults["uuid"]},
        )
        return geonode_resource

    def _update_existing_geonode_resource(self, geonode_resource, defaults):
    #     resource_files = defaults.get("files", [])
    #     geonode_resource = gs_resource_manager.update(
    #         geonode_resource,
    #         resource_type=geonode_resource_type,
    #         defaults=defaults,
    #         importer_session_opts={"name": defaults["uuid"]},
    #     )
        return geonode_resource

@lru_cache
def CSVParser(url: str):
    query_params = {"downloadformat": "csv"}
    response = requests.get(url, params=query_params)
    fn = slugify(url)+".csv"
    if not response.ok:
        return ""
    try:
        with open(fn, mode="wb") as file:
            file.write(response.content)
            return fn
    except:
        return ""

