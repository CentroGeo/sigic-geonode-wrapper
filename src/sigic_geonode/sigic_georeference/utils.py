from geonode.layers.models import Dataset


def get_name_from_ds(ds: Dataset) -> str:
    alt = ds.alternate
    alt_split = alt.split(":")
    if len(alt_split) != 2 or alt_split[0] != "geonode":
        raise Exception("Not a valid geonode database")
    return alt_split[1]
