import logging

from rest_framework import viewsets, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from .models import Request as SigicRequest
from .serializers import RequestSerializer

logger = logging.getLogger(__name__)




class RequestViewSet(viewsets.ModelViewSet):
    queryset = SigicRequest.objects.all()
    serializer_class = RequestSerializer
    permission_classes = [permissions.IsAuthenticated]
