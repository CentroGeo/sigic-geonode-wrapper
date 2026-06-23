from django.db import models
from geonode.base.models import ResourceBase
from django.conf import settings

STATUS_DEFAULT = 'pending'
STATUS = [
    ('on_review', 'On review'),
    ('pending', 'Pending'),
    ('published', 'Published'),
    ('rejected', 'Rejected'),
    ('editing', 'Editing'),
]

class Requests(models.Model):
    # class STATUS(models.TextChoices):
    #     ON_REVIEW = 'on_review', 'On review'
    #     PENDING = 'pending', 'Pending'
    #     PUBLISHED = 'published', 'Published'
    #     REJECTED = 'rejected', 'Rejected'

    # Cambiado de PROTECT a CASCADE para evitar que la eliminación de una capa
    # en GeoNode falle con ProtectedError si existe una solicitud de aprobación asociada.
    # Con CASCADE, al eliminar la capa, la solicitud se borra automáticamente en cascada.
    resource = models.ForeignKey(ResourceBase, on_delete=models.CASCADE)

    #owner
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviewer',
        null=True,
        blank=True,
        default=None
    )
    # todo hacer reviewer

    status = models.CharField(max_length=50, choices=STATUS, default=STATUS_DEFAULT)
    rejection_reason = models.TextField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)