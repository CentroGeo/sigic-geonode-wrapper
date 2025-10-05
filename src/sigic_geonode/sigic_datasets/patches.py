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
            # print("🔄 custom_partial_update - MultiValueDict", {k: data.get(k) for k in data.keys()})
            return {k: data.get(k) for k in data.keys()}
        
        # print("🔄 custom_partial_update - dict", dict(data))    
        return dict(data)

    # TODO: Hacer una función patch que permita la edición de los attribute set
    def change_attribute_set(data):
        data_dict = request_data_to_dict(data)
        attributes = data_dict.get("attribute_set")
        # print("🔄 custom_partial_update - attributes", attributes)

        if attributes == None:
            return
        
        attributes = eval(attributes)
        # print("🔄 custom_partial_update - eval", attributes)
        for pk_attribute in attributes.keys():
            # print("🔄 custom_partial_update - pk", pk_attribute)
            attribute = attributes.get(pk_attribute)
            # print("🔄 custom_partial_update - attribute", attribute)

            attr = Attribute.objects.get(pk=pk_attribute)
            # print("🔄 custom_partial_update - Attribute", attr)
            attr.description = attribute.get("description")
            attr.attribute_label = attribute.get("attribute_label")
            attr.visible = attribute.get("visible")
            attr.display_order = attribute.get("display_order")

            # for metadata_field in METADATA_FIELDS:
            #     if attribute.get(metadata_field) == None:
            #         continue

            #     print("🔄 custom_partial_update - metadata_field", metadata_field, attribute.get(metadata_field))
            #     attr[metadata_field] = attribute.get(metadata_field)
                
            attr.save()
    
    _orig_partial_update = DatasetViewSet.partial_update
    def custom_partial_update(self, request, *args, **kwargs):
        print("🔄 custom_partial_update - request", request.data)
        change_attribute_set(request.data)
        
        # dataset = self.get_object()
        # print("🔄 custom_partial_update - dataset:", dataset)

        return _orig_partial_update(self, request, *args, **kwargs)

        # return Response({
        #     "status": "ok",
        # })

    _orig_list = DatasetViewSet.list
    def custom_list(self, request, *args, **kwargs):
        """
        Sobrescribe el método list del DatasetViewSet
        """

        print("🧪 custom_list")
        return _orig_list(self, request, *args, **kwargs)


    # Inyectamos las funcionalidades a DatasetViewSet
    DatasetViewSet.partial_update = custom_partial_update
    DatasetViewSet.list = custom_list
    DatasetViewSet._patched_by_monkey = True
