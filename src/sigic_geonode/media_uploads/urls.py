from django.urls import path
from .views import upload_image_preview

urlpatterns = [
    path("ia", upload_image_preview, name="upload-project-preview"),
]