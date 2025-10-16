from rest_framework import serializers
from .models import Request as SigicRequest

class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model= SigicRequest
        fields = '__all__'