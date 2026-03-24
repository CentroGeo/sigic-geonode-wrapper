import traceback

from celery import chain as celery_chain
from geonode.base import enumerations
from geonode.layers.models import Attribute, Dataset, Style
from psycopg2.sql import SQL, Identifier
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from sigic_geonode.celeryapp import generate_column_styles, sync_geoserver
from sigic_geonode.utils.geodata_conn import connection

from .utils import get_dataset, get_name_from_ds


def _run_join_sql(cur, target_name, source_name, target_pivot, source_pivot, columns, reverse):
    """
    Execute ALTER TABLE + UPDATE SQL for a join operation.

    reverse=True  → target is the tabular layer; may receive a geometry column
    reverse=False → target is the geographic layer; only data columns are added
    """
    non_geom_cols = [c for c in columns if c != "geometry"]
    if non_geom_cols:
        cur.execute(
            SQL("ALTER TABLE {target} ADD {col_defs};").format(
                target=Identifier(target_name),
                col_defs=SQL(" VARCHAR, ADD ").join(
                    [Identifier(col) for col in non_geom_cols]
                ),
            )
        )

    if reverse and "geometry" in columns:
        cur.execute(
            SQL("SELECT srid FROM geometry_columns WHERE f_table_name=%s"),
            [source_name],
        )
        row = cur.fetchone()
        if row is None:
            raise Exception(f"No geometry_columns entry found for {source_name}")
        srid = row[0]
        cur.execute(
            SQL(
                'ALTER TABLE {target} ADD COLUMN "geometry" geometry(Geometry,%s);'
            ).format(target=Identifier(target_name)),
            [srid],
        )

    all_cols = columns  # includes "geometry" when reverse=True
    cur.execute(
        SQL(
            """
            UPDATE {target} SET {set_command}
            FROM (
                SELECT
                    {target}.ogc_fid,
                    {source}.{source_pivot},
                    {select_columns}
                FROM {target}
                JOIN {source}
                ON {target}.{target_pivot} = {source}.{source_pivot}
            ) AS subquery
            WHERE {target}.ogc_fid = subquery.ogc_fid;
            """
        ).format(
            target=Identifier(target_name),
            source=Identifier(source_name),
            select_columns=SQL(", ").join(
                [
                    SQL("{source}.{col}").format(
                        source=Identifier(source_name),
                        col=Identifier(col),
                    )
                    for col in all_cols
                ]
            ),
            target_pivot=Identifier(target_pivot),
            source_pivot=Identifier(source_pivot),
            set_command=SQL(", ").join(
                [
                    SQL("{col} = subquery.{col}").format(col=Identifier(col))
                    for col in all_cols
                ]
            ),
        )
    )


class JoinDataframes(APIView):
    def post(self, request: Request):
        request_data: dict = request.data
        ds = get_dataset(request_data.get("layer", -1))
        geo_ds = get_dataset(request_data.get("geo_layer", -1))
        layer_name: str = get_name_from_ds(ds)
        geo_name: str = get_name_from_ds(geo_ds)
        layer_pivot: str = request_data.get("layer_pivot", "")
        geo_pivot: str = request_data.get("geo_pivot", "")
        columns: list[str] = request_data.getlist("columns", [])
        reverse: bool = request_data.get("reverse", "false").lower() == "true"

        # Resolve target (dataset being modified) and source (dataset providing data)
        if reverse:
            target_ds, target_name = ds, layer_name
            source_ds, source_name = geo_ds, geo_name
            target_pivot, source_pivot = layer_pivot, geo_pivot
        else:
            target_ds, target_name = geo_ds, geo_name
            source_ds, source_name = ds, layer_name
            target_pivot, source_pivot = geo_pivot, layer_pivot

        with connection.cursor() as cur:
            if target_ds.state not in [
                enumerations.STATE_PROCESSED,
                enumerations.STATE_INCOMPLETE,
            ]:
                return Response(
                    {
                        "status": (
                            f"data not in valid state, currently {target_ds.state}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            target_ds.state = enumerations.STATE_RUNNING
            target_ds.save()
            try:
                _run_join_sql(
                    cur,
                    target_name,
                    source_name,
                    target_pivot,
                    source_pivot,
                    columns,
                    reverse,
                )
            except Exception as e:
                connection.rollback()
                target_ds.state = enumerations.STATE_INCOMPLETE
                target_ds.save()
                return Response(
                    {
                        "status": "failed running database changes",
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            self.update_attributes(target_ds, source_ds, columns, reverse)
        except Exception:
            connection.rollback()
            target_ds.state = enumerations.STATE_INCOMPLETE
            target_ds.save()
            return Response(
                {"status": "failed updating attributes"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data_columns = [c for c in columns if c != "geometry"]
        try:
            celery_chain(
                sync_geoserver.s(target_ds.id),
                generate_column_styles.si(target_ds.id, data_columns),
            ).apply_async()
        except Exception as e:
            connection.rollback()
            target_ds.state = enumerations.STATE_INCOMPLETE
            target_ds.save()
            return Response(
                {"status": "failed syncing geoserver", "msg": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        connection.commit()
        target_ds.state = enumerations.STATE_WAITING
        target_ds.save()
        return Response({"status": "success"})

    def update_attributes(
        self,
        target_ds: Dataset,
        source_ds: Dataset,
        columns: list,
        reverse: bool,
    ):
        """
        Update GeoNode Attribute records and geographic metadata.

        reverse=True  (geo → tabular):
            Creates Attribute records on target_ds and copies style/SRID/bbox
            from source_ds (the geographic layer).
        reverse=False (tabular → geo):
            Creates Attribute records on target_ds (the geographic layer).
            Does NOT touch style/SRID/bbox — the geo layer already has them.
        """
        for col in columns:
            if col == "geometry":
                if not reverse:
                    # Geometry already exists on the geo layer
                    continue
                attribute_type = source_ds.attributes.get(
                    attribute="geometry"
                ).attribute_type
            else:
                attribute_type = "xsd:string"

            Attribute.objects.get_or_create(
                dataset_id=target_ds.id,
                attribute=col,
                defaults={
                    "attribute_type": attribute_type,
                    "display_order": 100,
                },
            )

        if reverse:
            sty = Style.objects.get(id=source_ds.default_style_id)
            sty.dataset_styles.set([*sty.dataset_styles.all(), target_ds])
            target_ds.default_style_id = source_ds.default_style_id
            target_ds.srid = source_ds.srid
            target_ds.ll_bbox_polygon = source_ds.ll_bbox_polygon
            target_ds.bbox_polygon = source_ds.bbox_polygon
            target_ds.save()


class Status(APIView):
    def get(self, _request, layer: int):
        ds = get_dataset(layer)
        return Response({"status": str(ds.state)})


class Reset(APIView):
    def post(self, request):
        try:
            request_data: dict = request.data
            ds = get_dataset(request_data.get("layer", -1))
            sync_geoserver.apply_async((ds.id,))
        except Exception as e:
            return Response(
                {"status": "failed", "msg": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"status": "success"})
