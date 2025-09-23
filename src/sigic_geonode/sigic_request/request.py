import logging

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class Index(APIView):
    def get(self, request: Request):

        return Response({
            "status": "Index success",
        })

class Approval(APIView):
    def post(self, request: Request):
        # Requiere: user, recurso
        request_data: dict[str, str] = request.data
        
        return Response({
            "status": "success",
            "user": request_data.get("user", ""),
            "recurso": request_data.get("recurso", ""),
            "msg": request_data.get("msg", ""),
        })

class Test(APIView):
    # ''
    def get(self, request: Request):

        return Response({
            "status": "Test success",
        })
