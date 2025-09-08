from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes
import os
import mimetypes

@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_image_preview(request):
    
    if request.method == 'POST':
        file = request.FILES.get("file")
        category = request.POST.get("category")
        
        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        filename = file.name
        
        if(category == "proyectos"):
            upload_dir = os.path.join(settings.MEDIA_ROOT, "ia", "uploads", "projects")
        else:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "ia", "uploads", "contexts")
            
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)

        # Guardado en disco
        with open(save_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return JsonResponse({
            "message": "File uploaded successfully",
            "url": f"{settings.MEDIA_URL}{filename}"
        })

@api_view(["GET", "POST"])
def upload_status(request):
    if request.method == 'POST':
        filename = request.POST.get("filename")
        
        previews_dir = os.path.join(settings.MEDIA_ROOT, "ia", "uploads", "contexts")
        file_path = os.path.join(previews_dir, filename)

        if not os.path.exists(file_path):
            raise Http404("Archivo no encontrado")

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        return FileResponse(open(file_path, "rb"), content_type=mime_type)