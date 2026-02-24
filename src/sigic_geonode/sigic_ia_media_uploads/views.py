from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
import os
import mimetypes

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".pptx",'.json','.geojson','.docx','.doc','.csv'}
ALLOWED_DOCUMENT_FILE_EXTENSIONS = {'.pdf', '.pptx', '.docx', '.doc', '.json', '.geojson', '.csv'}
MAX_FILE_SIZE = 50 * 1024 * 1024

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_image_preview(request):
    
    if request.method == 'POST':
        file = request.FILES.get("file")
        url = ''
        
        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)


        filename = os.path.basename(file.name)
        filename = filename.replace(" ", "_")
        
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return Response({"error": f"Invalid file type: {ext}"}, status=400)
        
        if file.size > MAX_FILE_SIZE:
            return Response({"error": "File too large"}, status=400)
        
        if ext in ALLOWED_DOCUMENT_FILE_EXTENSIONS:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "ia", "uploads", "documents")
            url = f"{settings.MEDIA_URL}ia/uploads/documents/{filename}"
        else:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "ia", "uploads", "contexts")
            url = f"{settings.MEDIA_URL}ia/uploads/contexts/{filename}"
        
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)

        # Guardado en disco
        with open(save_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return JsonResponse({
            "message": "File uploaded successfully",
            "url": url
        })
