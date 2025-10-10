import logging

from django.utils.datastructures import MultiValueDict
from geonode.layers.api.views import DatasetViewSet
from geonode.layers.models import Attribute
from rest_framework.response import Response


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
        request_data_dict = request_data_to_dict(request_data)
        request_attributes = request_data_dict.get("attribute_set")

        if request_attributes == None:
            return
        
        dataset = self.get_object()
        print("🔄 custom_partial_update - dataset:", dataset)
        # print("🔄 custom_partial_update - attribute_set:", dataset.get("attribute_set"))
        
        request_attributes_dic = eval(request_attributes)
        for pk_attribute in request_attributes_dic.keys():
            # TODO: validar que no se modifiquen atributos ue no pertenezcan a la capa
            # if attribute.get(metadata_field) == None:
            #     continue

            request_attribute = request_attributes_dic.get(pk_attribute)
            geonpode_attribute = Attribute.objects.get(pk=pk_attribute)

            if request_attribute.get("attribute_label"):
                geonpode_attribute.attribute_label = request_attribute.get("attribute_label")
            if request_attribute.get("description"):
                geonpode_attribute.description = request_attribute.get("description")
            if request_attribute.get("display_order"):
                geonpode_attribute.display_order = request_attribute.get("display_order")
            if request_attribute.get("visible"):
                geonpode_attribute.visible = request_attribute.get("visible")
            
            # for metadata_field in METADATA_FIELDS:
            #     if attribute.get(metadata_field) == None:
            #         continue

            #     print("🔄 custom_partial_update - metadata_field", metadata_field, attribute.get(metadata_field))
            #     attr[metadata_field] = attribute.get(metadata_field)
                
            geonpode_attribute.save()
    
    _orig_partial_update = DatasetViewSet.partial_update
    def custom_partial_update(self, request, *args, **kwargs):
        print("🔄 custom_partial_update - request", request.data)
        change_attribute_set(self, request.data)

        return _orig_partial_update(self, request, *args, **kwargs)
    

    # Inyectamos las funcionalidades a DatasetViewSet
    DatasetViewSet.partial_update = custom_partial_update
    DatasetViewSet._patched_by_monkey = True
