from sigic_geonode.remote_services.file_handler import FileServiceHandler

class FileServiceInfo():
    services_type = {
        "File": {
            "OWS": False,
            "handler": FileServiceHandler,
            "label": "File Service",
            "management_view": "sigic_geonode.remote_services.file_view.FileView"
        }
    }

