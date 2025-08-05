import csv
import requests
from functools import lru_cache

from geonode.harvesting.harvesters.base import BaseHarvesterWorker
from geonode.base.models import ResourceBase
from geonode.layers.models import Dataset

class CSVHarvester(BaseHarvesterWorker):
    http_session: requests.Session

    def __init__(self, remote_url: str, harvester_id: int):
        super().__init__(remote_url, harvester_id)
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
        return [self.get_resource()]

    def check_availability(self, timeout_seconds = 5):
        return True

    def get_resource(self, harvestable_resource: "HarvestableResource"):
        #return HarvestedResourceInfo
        download = self.http_session.get(harvestable_resource.unique_identifier)

        # if download.status_code != requests.codes.ok:
            # return ""

        decoded_content = download.content.decode('utf-8')
        return csv.reader(decoded_content.splitlines(), delimiter=',')

@lru_cache
def CSVParser(url):
    response = urllib2.urlopen(url)
    return csv.reader(response)

