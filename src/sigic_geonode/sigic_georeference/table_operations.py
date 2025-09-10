import json

import requests
from django.conf import settings
from geonode.base.auth import get_or_create_token
from geonode.layers.models import Attribute, Dataset, Style
from geonode.people.models import Profile
from psycopg2.sql import SQL, Identifier
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
        layer_name: str = self.get_name_from_ds(ds)
        geo_name: str = self.get_name_from_ds(geo_ds)
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
                    # TODO Use previous table geometry
                    cur.execute(
                        SQL(
                            'ALTER TABLE {layer_table} ADD COLUMN "geometry" geometry(Geometry,32614);'
                        ).format(layer_table=Identifier(layer_name))
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
            except Exception:
                connection.rollback()
                return Response({"bye": "response"})
        try:
            self.update_attributes(ds, geo_ds, columns)
        except Exception:
            connection.rollback()
            return Response({"status": "failed updating attributes"})
        if not self.update_gs_features(layer_name):
            connection.rollback()
            return Response({"status": "failed"})
        connection.commit()
        return Response({"status": "success"})

    def get_name_from_ds(self, ds: Dataset):
        alt = ds.alternate
        alt_split = alt.split(":")
        if len(alt_split) != 2 or alt_split[0] != "geonode":
            raise Exception("Not a valid geonode database")
        return alt_split[1]

    def update_attributes(self, ds: Dataset, geo_ds: Dataset, columns):
        for col in columns:
            attribute_type = "xsd:string"
            if col == "geometry":
                attribute_type = geo_ds.attributes.get(
                    attribute="geometry"
                ).attribute_type
            Attribute.objects.create(
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

    def update_gs_features(self, layer, geo_layer):
        user = Profile.objects.get(id=1000)
        gs_server = settings.GEOSERVER_LOCATION
        url = f"{gs_server}rest/workspaces/geonode/datastores/{settings.GEONODE_GEODATABASE}/featuretypes"
        response = requests.get(
            f"{url}/{layer}.json",
            headers={"Authorization": f"Bearer {str(get_or_create_token(user))}"},
        )
        feature_types = response.json()
        response = requests.get(
            f"{url}/{geo_layer}.json",
            headers={"Authorization": f"Bearer {str(get_or_create_token(user))}"},
        )
        new_srs = response.json()["featureType"]["srs"]
        feature_types["featureType"]["srs"] = new_srs
        response = requests.put(
            f"{url}/{layer}.json?recalculate=nativebbox,latlonbbox",
            data=json.dumps(feature_types),
            headers={
                "Authorization": f"Bearer {str(get_or_create_token(user))}",
                "Content-Type": "application/json",
            },
        )
        return response.status_code == 200
