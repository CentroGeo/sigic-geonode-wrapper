# from importer.handlers.csv.handler import ImporterViewSet

class CSVService():
    services_type = {"CSV": {"OWS": False, "handler": "importer.handlers.csv.handler.CSVFileHandler", "label": "CSV Test", "management_view": "sigic_geonode.services.csv_view.CSVView"}}
    # services_type = {"CSV": {"OWS": False, "handler": "CSVFileHandler", "label": "CSV Test", "management_view": "sigic_geonode.services.csv_view.CSVView"}}
