import logging
import json

from django.utils.datastructures import MultiValueDict
from geonode.layers.api.views import DatasetViewSet
from geonode.layers.models import Attribute
# from rest_framework.response import Response


logger = logging.getLogger(__name__)

# Metadatos de los atributos del dataset permitidos para modificar
METADATA_FIELDS = {
    # "pk",
    # "attribute",
    "description",
    "attribute_label",
    # "attribute_type",
    "visible",
    "display_order",
    # "featureinfo_type",
    # "count",
    # "min",
    # "max",
    # "average",
    # "median",
    # "stddev",
    # "sum",
    # "unique_values",
    # "last_stats_updated",
}

# Evita aplicar el parche dos veces
if not getattr(DatasetViewSet, "_patched_by_monkey", False):

    def request_data_to_dict(data):
        if isinstance(data, MultiValueDict):
            return { k: data.get(k) for k in data.keys() }
        
        return dict(data)

    # Modifica los metadatos de los atributos existentes en la capa
    def change_attribute_set(self, request_data):
        logger.debug("🚀🚀 change_attribute_set ejecutado")

        request_data_dict = request_data_to_dict(request_data)
        request_attributes = request_data_dict.get("attribute_set")

        if request_attributes is None:
            return
        
        # request_attributes_dic = eval(request_attributes)
        request_attributes_dic = json.loads(request_attributes)
        request_attributes_dic_keys = request_attributes_dic.keys()
        # print("🔄 custom_partial_update - request_attributes_dic_keys:", request_attributes_dic_keys)

        for geonode_attribute in Attribute.objects.filter(dataset=self.get_object()):
            if (str(geonode_attribute.pk) not in request_attributes_dic_keys):
                continue

            request_attribute = request_attributes_dic.get(str(geonode_attribute.pk))

            if request_attribute.get("attribute_label") is not None:
                geonode_attribute.attribute_label = request_attribute.get("attribute_label")

            if request_attribute.get("description") is not None:
                geonode_attribute.description = request_attribute.get("description")

            if request_attribute.get("display_order") is not None:
                geonode_attribute.display_order = request_attribute.get("display_order")

            if request_attribute.get("visible") is not None:
                request_attribute_visible = request_attribute.get("visible")
                print("🔄 custom_partial_update - json.loads.visible", request_attribute_visible)
                if isinstance(request_attribute_visible, bool):
                    geonode_attribute.visible = request_attribute_visible
                elif isinstance(request_attribute_visible, str):
                    geonode_attribute.visible = request_attribute_visible.lower() == "true"
            
            # for metadata_field in METADATA_FIELDS:
            #     if attribute.get(metadata_field) is None:
            #         continue

            #     print("🔄 custom_partial_update - metadata_field", metadata_field, attribute.get(metadata_field))
            #     attr[metadata_field] = attribute.get(metadata_field)

            geonode_attribute.save()
    
    _orig_partial_update = DatasetViewSet.partial_update
    def custom_partial_update(self, request, *args, **kwargs):
        # print("🔄 custom_partial_update - request", request.data)
        change_attribute_set(self, request.data)

        return _orig_partial_update(self, request, *args, **kwargs)
    

    # Inyectamos las funcionalidades a DatasetViewSet
    DatasetViewSet.partial_update = custom_partial_update
    DatasetViewSet._patched_by_monkey = True
