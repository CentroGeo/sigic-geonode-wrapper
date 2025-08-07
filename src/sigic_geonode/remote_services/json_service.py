class JSONService():
    services_type = {
        "JSON": {"OWS": False, "handler": "JSONHandler", "label": "JSON Test", "management_view": "sigic_geonode.remote_services.json_view.JSONView"},
        "GeoJSON": {"OWS": False, "handler": "GeoJSONHandler", "label": "GeoJSON Test", "management_view": "sigic_geonode.remote_services.json_view.JSONView"},
    }
