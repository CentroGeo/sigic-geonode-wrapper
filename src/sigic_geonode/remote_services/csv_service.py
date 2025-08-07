from sigic_geonode.remote_services.csv_handler import CSVServiceHandler

class CSVServiceInfo():
    services_type = {
        "CSV": {
            "OWS": False,
            "handler": CSVServiceHandler,
            "label": "CSV Service",
            "management_view": "sigic_geonode.remote_services.csv_view.CSVView"
        }
    }

