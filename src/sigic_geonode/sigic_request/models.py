from django.db import models
from django.conf import settings
from geonode.base.models import ResourceBase

STATUS_DEFAULT = 'pending'
STATUS = [
    ('on_review', 'On review'),
    ('pending', 'Pending'),
    ('published', 'Published'),
    ('rejected', 'Rejected'),
]

class Request(models.Model):
    # class STATUS(models.TextChoices):
    #     ON_REVIEW = 'on_review', 'On review'
    #     PENDING = 'pending', 'Pending'
    #     PUBLISHED = 'published', 'Published'
    #     REJECTED = 'rejected', 'Rejected'

    resource = models.ForeignKey(ResourceBase, on_delete=models.PROTECT)

    #owner
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reviewer', null=True, blank=True,default=None)
    # todo hacer reviewer

    status = models.CharField(max_length=50, choices=STATUS, default=STATUS_DEFAULT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
