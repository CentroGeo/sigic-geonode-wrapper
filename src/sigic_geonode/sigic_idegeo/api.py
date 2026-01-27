from ninja import NinjaAPI
from ninja.security import django_auth

from idegeo.geo_stories.api import router as geostories_router
from idegeo.GeonodeModels.api import router as geonode_router
from idegeo.escenas.api import router as escenas_router

api = NinjaAPI(auth=django_auth)

api.add_router("/geostories/", geostories_router)
api.add_router("/geonode/", geonode_router)
api.add_router("/escenas/", escenas_router)