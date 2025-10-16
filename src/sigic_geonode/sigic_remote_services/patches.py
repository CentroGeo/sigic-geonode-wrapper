import logging

from geonode.base import enumerations
from geonode.base.utils import ResourceBase
from geonode.harvesting.harvesters.base import (
    BaseHarvesterWorker,
    HarvestedResourceInfo,
)
from geonode.harvesting.models import HarvestedResource

logger = logging.getLogger(__name__)


if not getattr(BaseHarvesterWorker, "_patched_by_monkey", False):
    _orig_finalize_resource_update = BaseHarvesterWorker.finalize_resource_update

    def custom_finalize_resource_update(
        self,
        geonode_resource: ResourceBase,
        harvested_info: HarvestedResourceInfo,
        harvestable_resource: HarvestedResource,
    ) -> ResourceBase:
        try:
            logger.debug("custom_finalize_resource_update")
            if (
                geonode_resource.abstract is None
                or geonode_resource.title is None
                or geonode_resource.keywords is None
                or geonode_resource.language is None
            ):
                logger.warning(
                    f"Geonode resource {str(harvested_info.resource_descriptor.uuid)} not in valid state"
                )
                geonode_resource.state = enumerations.STATE_INVALID
                geonode_resource.set_dirty_state()
                geonode_resource.save()
            return _orig_finalize_resource_update(
                self, geonode_resource, harvested_info, harvestable_resource
            )
        except Exception as e:
            logger.warning(f"Error en custom_get_queryset: {e}")
            return _orig_finalize_resource_update(
                self, geonode_resource, harvested_info, harvestable_resource
            )

    # Inyectamos las funcionalidades a ResourceBaseViewSet
    BaseHarvesterWorker.finalize_resource_update = custom_finalize_resource_update
    BaseHarvesterWorker._patched_by_monkey = True
