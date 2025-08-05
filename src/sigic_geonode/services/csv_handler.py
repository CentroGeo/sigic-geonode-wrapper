import logging

from uuid import uuid4

from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from geonode import GeoNodeException
from geonode.harvesting.models import Harvester
from sigic_geonode.services.csv_harvester import CSVParser

from geonode.services import models, enumerations
from geonode.services.serviceprocessors import base

logger = logging.getLogger(__name__)

class CSVServiceHandler(base.ServiceHandlerBase):
    """Remote service handler for ESRI:ArcGIS:MapServer services"""

    service_type = "CSV"

    def __init__(self, url, geonode_service_id=None, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        base.ServiceHandlerBase.__init__(self, url, geonode_service_id)

        self.indexing_method = enumerations.INDEXED
        self.name = slugify(url)[:255]
        # self.title = str(_title).encode("utf-8", "ignore").decode("utf-8")
        self.title = slugify(url)[:255]

    @property
    def parsed_service(self):
        return CSVParser(self.url)

    def probe(self):
        # TODO Logica para verificar que es un archivo válido
        return True
        # try:
        #     return True if len(self.parsed_service._json_struct) > 0 else False
        # except Exception:
        #     return False

    def create_cascaded_store(self, service):
        return None

    def create_geonode_service(self, owner, parent=None):
        """Create a new geonode.service.models.Service instance

        :arg owner: The user who will own the service instance
        :type owner: geonode.people.models.Profile

        """
        with transaction.atomic():
            # TODO initializa modelo
            instance = models.Service.objects.create(
                uuid=str(uuid4()),
                base_url=self.url,
                type=self.service_type,
                method=self.indexing_method,
                owner=owner,
                # metadata_only=True,
                metadata_only=False,
            #     version=str(self.parsed_service._json_struct.get("currentVersion", 0.0))
            #     .encode("utf-8", "ignore")
            #     .decode("utf-8"),
                version="ignore",
                name=self.name,
                title=self.title,
            #     abstract=str(self.parsed_service._json_struct.get("serviceDescription"))
            #     .encode("utf-8", "ignore")
            #     .decode("utf-8")
            #     or _("Not provided"),
                abstract = "Not provided",
            )

            # TODO initializa el Harvester
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
        # TODO Tener lógica de palabras claves
        return ["TODO", "prueba", "palabras", "clave"]
        # return self.parsed_service._json_struct.get("capabilities", "").split(",")

    def get_harvester_type(self):
        return "sigic_geonode.services.csv_harvester.CSVHarvester"

    def get_harvester_configuration_options(self):
        #TODO llenar según el harvester
        return {}

    # def _parse_datasets(self, layers):
    #     map_datasets = []
    #     for lyr in layers:
    #         map_datasets.append(self._dataset_meta(lyr))
    #         map_datasets.extend(self._parse_datasets(lyr.subLayers))
    #     return map_datasets

    # def _dataset_meta(self, layer):
    #     _ll_keys = [
    #         "id",
    #         "title",
    #         "abstract",
    #         "type",
    #         "geometryType",
    #         "copyrightText",
    #         "extent",
    #         "fields",
    #         "minScale",
    #         "maxScale",
    #     ]
    #     _ll = {}
    #     if isinstance(layer, dict):
    #         for _key in _ll_keys:
    #             _ll[_key] = layer[_key] if _key in layer else None
    #     else:
    #         for _key in _ll_keys:
    #             _ll[_key] = getattr(layer, _key, None)
    #     if not _ll["title"] and getattr(layer, "name"):
    #         _ll["title"] = getattr(layer, "name")
    #     return MapLayer(**_ll)

    # def _offers_geonode_projection(self, srs):
    #     geonode_projection = getattr(settings, "DEFAULT_MAP_CRS", "EPSG:3857")
    #     return geonode_projection in f"EPSG:{srs}"

    # def _get_indexed_dataset_fields(self, dataset_meta):
    #     srs = f"EPSG:{dataset_meta.extent.spatialReference.wkid}"
    #     bbox = utils.decimal_encode(
    #         [dataset_meta.extent.xmin, dataset_meta.extent.ymin, dataset_meta.extent.xmax, dataset_meta.extent.ymax]
    #     )
    #     typename = slugify(f"{dataset_meta.id}-{''.join(c for c in dataset_meta.title if ord(c) < 128)}")
    #     return {
    #         "name": dataset_meta.title,
    #         "store": self.name,
    #         "subtype": "remote",
    #         "workspace": "remoteWorkspace",
    #         "typename": typename,
    #         "alternate": f"{slugify(self.url)}:{dataset_meta.id}",
    #         "title": dataset_meta.title,
    #         "abstract": dataset_meta.abstract,
    #         "bbox_polygon": BBOXHelper.from_xy([bbox[0], bbox[2], bbox[1], bbox[3]]).as_polygon(),
    #         "srid": srs,
    #         "keywords": ["ESRI", "ArcGIS REST MapServer", dataset_meta.title],
    #     }

