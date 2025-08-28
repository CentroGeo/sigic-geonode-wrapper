from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.


class LinkWebSite(models.Model):
    title = models.CharField(verbose_name=_("Nombre"), max_length=150)
    image = models.ImageField(
        verbose_name=_("Imagen"), upload_to="link_web_site/image/"
    )
    url = models.URLField(max_length=200)

    class Meta:
        verbose_name = "Link Web Site"
        verbose_name_plural = "Links Web Site"
        ordering = ["title"]

    def __str__(self):
        return self.title
