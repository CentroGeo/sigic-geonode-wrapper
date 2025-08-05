from geonode.harvesting.harvesters.base import BaseHarvesterWorker

class CSVHarvester(BaseHarvesterWorker):
    @classmethod
    def from_django_record(cls, harvester: "Harvester"):
        # inicializar desde record de django
        pass

    def get_num_available_resources(self):
        # Regresar cuantos recursos
        return 1

    def list_resources(self, offset = 0):
        # regresar lista de recursos
        []

    def check_availability(self, timeout_seconds = 5):
        return True

    def get_resource(self, harvestable_resource: "HarvestableResource"):
        #return HarvestedResourceInfo
        pass

