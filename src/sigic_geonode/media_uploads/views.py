from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes
import os

@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_image_preview(request):
    
    if request.method == 'POST':
        file = request.FILES.get("file")
        category = request.POST.get("category")
        
        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        filename = f"{timezone.now().strftime('%Y%m%d%H%M%S')}_{file.name}"
        
        if(category == "proyectos"):
            upload_dir = os.path.join(settings.MEDIA_ROOT, "IA", "uploads", "proyectos")
        else:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "IA", "uploads", "contextos")
            
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