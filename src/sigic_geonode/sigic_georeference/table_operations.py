import json
import os

import requests
from geonode.layers.models import Attribute, Dataset, Style
from psycopg2.sql import SQL, Identifier
from requests.auth import HTTPBasicAuth
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from sigic_geonode.sigic_helper.geodata_conn import connection


class JoinDataframes(APIView):
    def post(self, request: Request):
        request_data: dict[str, str] = request.data
        ds: Dataset = Dataset.objects.filter(id=request_data.get("layer", -1)).first()
        geo_ds: Dataset = Dataset.objects.filter(
            id=request_data.get("geo_layer", -1)
        ).first()
        if ds is None:
            raise Exception(f"Dataset {request_data.get('layer', -1)} does not exist")
        if geo_ds is None:
            raise Exception(
                f"Dataset {request_data.get('geo_layer', -1)} does not exist"
            )
        layer_name: str = get_name_from_ds(ds)
        geo_name: str = get_name_from_ds(geo_ds)
        layer_pivot: str = request_data.get("layer_pivot", "")
        geo_pivot: str = request_data.get("geo_pivot", "")
        columns: list[str] = request_data.getlist("columns", [])

        with connection.cursor() as cur:
            try:
                cur.execute(
                    SQL("ALTER TABLE {layer_table} ADD {columns}VARCHAR;").format(
                        columns=SQL(" VARCHAR, ADD ").join(
                            [Identifier(col) for col in columns if col != "geometry"]
                        ),
                        layer_table=Identifier(layer_name),
                    )
                )
                if "geometry" in columns:
                    cur.execute(
                        SQL(
                            f"""SELECT srid FROM geometry_columns
                            WHERE f_table_name='{geo_name}'"""
                        )
                    )
                    srid = cur.fetchone()[0]
                    cur.execute(
                        SQL(
                            f'ALTER TABLE {layer_name} ADD COLUMN "geometry" geometry(Geometry,{srid});'
                        )
                    )
                cur.execute(
                    SQL(
                        """
                        UPDATE {layer_table} SET {set_command} FROM (
                            SELECT
                                {layer_table}.ogc_fid,
                                {geo_table}.{geo_pivot},
                                {select_columns}
                            FROM {layer_table}
                            JOIN {geo_table}
                            ON {layer_table}.{layer_pivot}={geo_table}.{geo_pivot}
                        ) as subquery
                        WHERE {layer_table}.ogc_fid=subquery.ogc_fid;
                    """
                    ).format(
                        layer_table=Identifier(layer_name),
                        geo_table=Identifier(geo_name),
                        select_columns=SQL(", ").join(
                            [
                                SQL("{geo_table}.{col}").format(
                                    geo_table=Identifier(geo_name), col=Identifier(col)
                                )
                                for col in columns
                            ]
                        ),
                        layer_pivot=Identifier(layer_pivot),
                        geo_pivot=Identifier(geo_pivot),
                        set_command=SQL(", ").join(
                            [
                                SQL("{col} = subquery.{col}").format(
                                    col=Identifier(col)
                                )
                                for col in columns
                            ]
                        ),
                    )
                )
            except Exception as e:
                connection.rollback()
                return Response({"status": "failed", "error": str(e)})
        try:
            self.update_attributes(ds, geo_ds, columns)
        except Exception:
            connection.rollback()
            return Response({"status": "failed updating attributes"})
        connection.commit()
        return Response({"status": "success"})

    def update_attributes(self, ds: Dataset, geo_ds: Dataset, columns):
        # Modificar los attributos dentro de postgres
        for col in columns:
            attribute_type = "xsd:string"
            if col == "geometry":
                attribute_type = geo_ds.attributes.get(
                    attribute="geometry"
                ).attribute_type
            _ = Attribute.objects.create(
                dataset_id=ds.id,
                attribute_type=attribute_type,
                attribute=col,
                display_order=100,
            )
        sty = Style.objects.get(id=geo_ds.default_style_id)
        sty.dataset_styles.set([*sty.dataset_styles.all(), ds])
        ds.default_style_id = geo_ds.default_style_id
        ds.srid = geo_ds.srid
        ds.ll_bbox_polygon = geo_ds.ll_bbox_polygon
        ds.bbox_polygon = geo_ds.bbox_polygon
        ds.save()


class Reset(APIView):
    def post(self, request):
        gs_server = os.getenv("GEOSERVER_LOCATION", "")
        url = f"{gs_server}rest/workspaces/geonode/datastores/sigic_geonode_data/featuretypes"

        ds: Dataset = Dataset.objects.filter(id=request.data.get("layer", -1)).first()
        layer = get_name_from_ds(ds)

        # Obtener los datos actuales para sobrescribir
        response = requests.get(
            f"{url}/{layer}.json",
            auth=HTTPBasicAuth(
                username=os.getenv("GEOSERVER_ADMIN_USER", ""),
                password=os.getenv("GEOSERVER_ADMIN_PASSWORD", ""),
            ),
            timeout=15,
        )

        # Enviar nuevos datos con commando de recalcular nativebbox/latlogbbox
        feature_types = response.json()
        feature_types["featureType"]["srs"] = "EPSG:32614"

        response = requests.put(
            f"{url}/{layer}.json?recalculate=nativebbox,latlonbbox",
            data=json.dumps(feature_types),
            auth=HTTPBasicAuth(
                username=os.getenv("GEOSERVER_ADMIN_USER", ""),
                password=os.getenv("GEOSERVER_ADMIN_PASSWORD", ""),
            ),
            headers={"Content-Type": "application/json"},
            timeout=15,
        )

        if response.status_code != 200:
            return Response({"status": "failed"})
        return Response(
            {"status": "success", "layer": layer, "response": response.content}
        )


def get_name_from_ds(ds: Dataset):
    alt = ds.alternate
    alt_split = alt.split(":")
    if len(alt_split) != 2 or alt_split[0] != "geonode":
        raise Exception("Not a valid geonode database")
    return alt_split[1]
