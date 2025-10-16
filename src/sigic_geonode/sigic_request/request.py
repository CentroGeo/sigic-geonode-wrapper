import logging

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Request as SigicRequest

logger = logging.getLogger(__name__)

user = {
    "pk": 1001,
    "username": "psp.amartinez@centrogeo.edu.mx",
    "first_name": "Andrés",
    "last_name": "Martínez",
    "avatar": "http://localhost/static/geonode/img/avatar.png",
    "is_superuser": False,
    "is_staff": False,
    "email": "psp.amartinez@centrogeo.edu.mx",
    "link": "http://localhost/api/v2/users/1001"
}

class Index(APIView):

    def get(self, request: Request):
        logger.debug("🚀🚀 get Requests ejecutado")
        print("💍 get Requests ejecutado")

        requests = [
            {
                "pk": 1,
                "resource": 1,
                "type": "aproval",
                "status": "",
                "date": "2025-10-01T23:43:31.293198Z",
                "last_updated": "2025-10-13T22:57:19.007939Z",
                "owner": user,
                "reviwer": user
            }
        ]

        return Response({
            "links": {
                "next": None,
                "previous": None,
            },
            "total": len(requests),
            "page": 1,
            "page_size": 10,
            "requests": requests
        })
    
    def post(self, request: Request):
        print("💍 post Requests ejecutado")

        print("💍 post Requests - user", request.user)

        obj = SigicRequest.objects.create(
            # resource_id=ser.validated_data["resource_id"],
            resource=1,
            # type="",
            # message='este es un mensaje de prueba',
            user=request.user,  # usa el user autenticado
        )


        print("💍 post Requests - obj", obj)

        # Requiere: user, recurso
        request_data: dict[str, str] = request.data
        
        return Response({
            "status": "success",
            # "user": request_data.get("user", ""),
            # "resource": request_data.get("resource", ""),
            # # "msg": request_data.get("msg", ""),
            # "type": request_data.get("type", ""),
        })


class Request(APIView):
    def patch(self, request: Request):
        return Response({
            "status": "Index success",
        })