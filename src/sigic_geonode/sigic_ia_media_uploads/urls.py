from django.urls import path
from .views import upload_image_preview

urlpatterns = [
    path("upload", upload_image_preview, name="upload-project-preview")
]