from sigic_geonode.services.csv_handler import CSVServiceHandler

class CSVServiceInfo():
    services_type = {
        "CSV": {
            "OWS": False,
            # "handler": "sigic_geonode.services.csv_handler.CSVServiceHandler",
            "handler": CSVServiceHandler,
            "label": "CSV Service",
            "management_view": "sigic_geonode.services.csv_view.CSVView"
        }
    }
    # services_type = {"CSV": {"OWS": False, "handler": "CSVFileHandler", "label": "CSV Test", "management_view": "sigic_geonode.services.csv_view.CSVView"}}

