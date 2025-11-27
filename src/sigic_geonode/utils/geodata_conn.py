import os

from psycopg2 import connect

connection = connect(
    database=os.getenv("GEONODE_GEODATABASE", ""),
    user=os.getenv("GEONODE_GEODATABASE_USER", ""),
    password=os.getenv("GEONODE_GEODATABASE_PASSWORD", ""),
    host=os.getenv("DATABASE_HOST", ""),
    port=os.getenv("DATABASE_PORT", ""),
)
