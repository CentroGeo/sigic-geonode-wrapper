import requests
import typing
from functools import lru_cache
from dataclasses import dataclass, field

from django.utils.text import slugify
from geonode.harvesting.resourcedescriptor import RecordDescription, RecordIdentification, RecordDistribution
from geonode.harvesting.harvesters.base import BaseHarvesterWorker
from geonode.base.models import ResourceBase
from geonode.layers.models import Dataset

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
                unique_identifier = self.name,
                title = self.title,
                resource_type = "dataset",
            )
        ]

    def check_availability(self, timeout_seconds = 5):
        # TODO Llenar
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

@lru_cache
def CSVParser(url: str):
    return ""
    # query_params = {"downloadformat": "csv"}
    # response = requests.get(url, params=query_params)
    # if response.ok:
    #     return response.content
    #     # return CSVResource(response.content)
    # return ""
