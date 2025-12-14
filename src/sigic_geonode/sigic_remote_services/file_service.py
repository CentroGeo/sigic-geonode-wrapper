from sigic_geonode.sigic_remote_services.file_handler import FileServiceHandler


class FileServiceInfo:
    services_type = {
        "FILE": {
            "OWS": False,
            "handler": FileServiceHandler,
            "label": "File Service",
            "management_view": "sigic_geonode.sigic_remote_services.file_view.FileView",
        }
    }
