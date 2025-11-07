from rest_framework import serializers


class SLDUploadSerializer(serializers.Serializer):
    dataset_name = serializers.CharField(required=True)
    sld_file = serializers.FileField(required=False, allow_null=True)
    sld_body = serializers.CharField(required=False, allow_blank=True)
    is_default = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        sld_file = data.get("sld_file")
        sld_body = data.get("sld_body")

        if not sld_file and not sld_body:
            raise serializers.ValidationError(
                "Debes enviar un archivo SLD o un cuerpo SLD en texto."
            )
        if sld_file and sld_body:
            raise serializers.ValidationError(
                "Envía solo uno: archivo o texto, no ambos."
            )
        return data
