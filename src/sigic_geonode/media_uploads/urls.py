from django.urls import path
from .views import upload_image_preview, upload_status

urlpatterns = [
    path("ia", upload_image_preview, name="upload-project-preview"),
    path("ia/register", upload_status, name="register-project-preview"),
]