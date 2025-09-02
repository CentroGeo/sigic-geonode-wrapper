import logging
from uuid import uuid4

from django.db import transaction
from geonode import GeoNodeException
from geonode.harvesting.models import Harvester
from geonode.services import enumerations, models
from geonode.services.serviceprocessors import base

from sigic_geonode.sigic_remote_services.file_harvester import url_parse_file

logger = logging.getLogger(__name__)

ACCEPTED_EXTENSIONS = {
    "csv": "CSV",
    "json": "JSON",
    "geojson": "GEOJSON",
    "xls": "EXCEL",
    "xlsx": "EXCEL",
}


class FileServiceHandler(base.ServiceHandlerBase):
    """Remote service handler for ESRI:ArcGIS:MapServer services"""

    service_type = "FILE"

    def __init__(self, url, geonode_service_id=None, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        base.ServiceHandlerBase.__init__(self, url, geonode_service_id)

        self.indexing_method: str = enumerations.INDEXED
        parsed: str = url_parse_file(self.url)
        self.name: str = parsed
        self.title: str = parsed

    @property
    def parsed_service(self):
        return url_parse_file(self.url)

    def probe(self):
        try:
            fn = self.parsed_service
            split = fn.split(".")
            if len(split) > 1 and split[-1] in ACCEPTED_EXTENSIONS.keys():
                return True
            logger.exception(
                f"Extension not recognized, use one of: {ACCEPTED_EXTENSIONS.keys()}"
            )
            return False
        except Exception:
            return False

    def create_cascaded_store(self, service):
        return None

    def create_geonode_service(self, owner, parent=None):
        """Create a new geonode.service.models.Service instance

        :arg owner: The user who will own the service instance
        :type owner: geonode.people.models.Profile

        """
        with transaction.atomic():
            instance = models.Service.objects.create(
                uuid=str(uuid4()),
                base_url=self.url,
                type=self.service_type,
                method=self.indexing_method,
                owner=owner,
                metadata_only=False,
                version="ignore",
                name=self.name,
                title=self.title,
                abstract="Not provided",
            )

            service_harvester = Harvester.objects.create(
                name=self.name,
                default_owner=owner,
                scheduling_enabled=False,
                remote_url=instance.service_url,
                delete_orphan_resources_automatically=True,
                harvester_type=self.get_harvester_type(),
                harvester_type_specific_configuration=self.get_harvester_configuration_options(),
            )

            if service_harvester.update_availability():
                service_harvester.initiate_update_harvestable_resources()
            else:
                logger.exception(GeoNodeException("Could not reach remote endpoint."))
            instance.harvester = service_harvester

        self.geonode_service_id = instance.id
        return instance

    def get_keywords(self):
        return []

    def get_harvester_type(self):
        return "sigic_geonode.sigic_remote_services.file_harvester.FileHarvester"

    def get_harvester_configuration_options(self):
        return {"harvest_datasets": True, "harvest_documents": True}
