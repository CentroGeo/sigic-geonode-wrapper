class CSVService():
    services_type = {
        "CSV": {
            "OWS": False,
            "handler": "sigic_geonode.services.csv_handler.CSVServiceHandler",
            "label": "CSV Test",
            "management_view": "sigic_geonode.services.csv_view.CSVView"
        }
    }
    # services_type = {"CSV": {"OWS": False, "handler": "CSVFileHandler", "label": "CSV Test", "management_view": "sigic_geonode.services.csv_view.CSVView"}}

