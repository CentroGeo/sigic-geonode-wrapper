from geonode.base import enumerations
from geonode.layers.models import Attribute, Dataset, Style
from psycopg2.sql import SQL, Identifier
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from sigic_geonode.celeryapp import sync_geoserver
from sigic_geonode.utils.geodata_conn import connection

from .utils import get_dataset, get_name_from_ds


class JoinDataframes(APIView):
    def post(self, request: Request):
        request_data: dict[str, str] = request.data
        ds = get_dataset(request_data.get("layer", -1))
        geo_ds = get_dataset(request_data.get("geo_layer", -1))
        layer_name: str = get_name_from_ds(ds)
        geo_name: str = get_name_from_ds(geo_ds)
        layer_pivot: str = request_data.get("layer_pivot", "")
        geo_pivot: str = request_data.get("geo_pivot", "")
        columns: list[str] = request_data.getlist("columns", [])

        with connection.cursor() as cur:
            if ds.state not in [
                enumerations.STATE_PROCESSED,
                enumerations.STATE_INCOMPLETE,
            ]:
                return Response(
                    {"status": f"data not in valid state, currently {ds.state}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ds.state = enumerations.STATE_RUNNING
            ds.save()
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
                            """SELECT srid FROM geometry_columns
                            WHERE f_table_name=%s"""
                        ),
                        [geo_name],
                    )
                    srid = cur.fetchone()[0]
                    cur.execute(
                        SQL(
                            'ALTER TABLE {layer_table} ADD COLUMN "geometry" geometry(Geometry,%s);'
                        ).format(layer_table=Identifier(layer_name)),
                        [srid],
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
                ds.state = enumerations.STATE_INCOMPLETE
                ds.save()
                return Response(
                    {"status": "failed running database changes"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            self.update_attributes(ds, geo_ds, columns)
        except Exception:
            connection.rollback()
            ds.state = enumerations.STATE_INCOMPLETE
            ds.save()
            return Response(
                {"status": "failed updating attributes"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sync_geoserver.apply_async((ds.id,))
        except Exception as e:
            connection.rollback()
            ds.state = enumerations.STATE_INCOMPLETE
            ds.save()
            return Response(
                {"status": "failed syncing geoserver", "msg": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        connection.commit()
        ds.state = enumerations.STATE_WAITING
        ds.save()
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


class Status(APIView):
    def get(self, _request, layer: int):
        ds = get_dataset(layer)
        return Response({"status": str(ds.state)})


class Reset(APIView):
    def post(self, request):
        try:
            request_data: dict[str, str] = request.data
            ds = get_dataset(request_data.get("layer", -1))
            sync_geoserver.apply_async((ds.id,))
        except Exception as e:
            return Response(
                {"status": "failed", "msg": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"status": "success"})
