from django.urls import path
from .views import upload_image_preview, upload_status

urlpatterns = [
    path("upload", upload_image_preview, name="upload-project-preview"),
    path("register", upload_status, name="register-project-preview"),
]