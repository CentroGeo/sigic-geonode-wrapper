from django.urls import path
from .views import upload_image_preview, delete_file_preview

urlpatterns = [
    path("upload", upload_image_preview, name="upload-project-preview"),
    path("delete", delete_file_preview, name="delete-file-preview")
]